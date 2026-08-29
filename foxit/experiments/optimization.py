#!/usr/bin/env python3
"""Derive optimal risk budgets with full audit chain.

For each risk level and document type:
1. What's the optimal threshold?
2. What coverage does it achieve?
3. What's the audit trail proving the decision?
"""

import os, sys, json
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUTPUT_DIR = "/tmp/proofdesk/derivation"
os.makedirs(OUTPUT_DIR, exist_ok=True)

plt.rcParams.update({
    "figure.facecolor": "#0d1117", "axes.facecolor": "#161b22",
    "axes.edgecolor": "#30363d", "axes.labelcolor": "#c9d1d9",
    "text.color": "#c9d1d9", "xtick.color": "#8b949e",
    "ytick.color": "#8b949e", "grid.color": "#21262d",
    "grid.alpha": 0.6, "figure.dpi": 150, "font.size": 10,
})
C = {"blue": "#58a6ff", "green": "#3fb950", "red": "#f85149",
     "orange": "#d29922", "purple": "#bc8cff", "cyan": "#39d2c0", "white": "#c9d1d9"}

def load_data():
    from datasets import load_dataset
    ds = load_dataset('jngb-labs/InvoiceBenchmark', split='test', token='os.environ.get('HF_TOKEN', '')')
    docs = []
    for item in ds:
        c = float(item['correct_total'])
        r = float(item['rendered_total'])
        is_correct = abs(c - r) < 0.01
        docs.append({
            'features': [c/10000, r/10000, abs(c-r)/1000, 1 if item['has_discount'] else 0, 1 if item['edge_case'] else 0],
            'label': 1 if is_correct else 0,
            'doc_type': 'invoice',
            'correct_total': c, 'rendered_total': r,
            'has_discount': item['has_discount'], 'edge_case': item['edge_case'],
        })
    return docs

def derive_optimal(docs):
    """Derive optimal thresholds with full audit chain."""
    from sklearn.linear_model import LogisticRegression
    
    X = np.array([d['features'] for d in docs])
    y = np.array([d['label'] for d in docs])
    
    lr = LogisticRegression(C=1.0, max_iter=1000)
    lr.fit(X, y)
    probs = lr.predict_proba(X)[:, 1]
    
    # Feature importance
    feature_names = ['correct_total', 'rendered_total', 'error', 'has_discount', 'edge_case']
    importance = dict(zip(feature_names, lr.coef_[0]))
    
    # Optimal thresholds per risk budget
    risk_budgets = [0.0, 0.01, 0.05, 0.10, 0.20]
    results = {}
    
    for alpha in risk_budgets:
        sorted_probs = np.sort(probs)
        idx = int(np.ceil((1 - alpha) * (1 + 1/len(sorted_probs)) * len(sorted_probs)))
        tau = sorted_probs[min(idx, len(sorted_probs)-1)]
        preds = (probs >= tau).astype(int)
        coverage = preds.mean()
        fp = int(np.sum((preds == 1) & (y == 0)))
        
        # Audit: which docs would be auto-signed?
        auto_signed = [docs[i] for i in range(len(docs)) if preds[i] == 1]
        reviewed = [docs[i] for i in range(len(docs)) if preds[i] == 0]
        
        results[f"{alpha:.0%}"] = {
            'threshold': float(tau),
            'coverage': float(coverage),
            'auto_sign': len(auto_signed),
            'review': len(reviewed),
            'false_signs': fp,
            'audit': {
                'auto_signed_docs': [{'doc': d['doc_type'], 'correct': d['label']==1} for d in auto_signed[:5]],
                'reviewed_docs': [{'doc': d['doc_type'], 'correct': d['label']==1} for d in reviewed[:5]],
                'feature_importance': {k: float(v) for k, v in importance.items()},
            }
        }
    
    return results, importance

def plot_derivation(results, importance):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Optimal Risk Budget Derivation — Full Audit Chain", fontsize=14, fontweight="bold", color=C["white"])
    
    alphas = [float(k.replace('%',''))/100 for k in results.keys()]
    coverages = [results[k]['coverage']*100 for k in results.keys()]
    
    # Coverage vs Risk Budget
    ax = axes[0][0]
    ax.plot([a*100 for a in alphas], coverages, 'o-', color=C["cyan"], linewidth=2, markersize=8)
    ax.set_xlabel("Risk Budget (%)"); ax.set_ylabel("Coverage (%)")
    ax.set_title("Optimal Auto-Sign vs Risk Budget")
    ax.grid(True, alpha=0.2)
    
    # Feature importance
    ax = axes[0][1]
    features = list(importance.keys())
    values = [abs(v) for v in importance.values()]
    ax.barh(features, values, color=[C["green"] if v > 0.5 else C["orange"] for v in values], alpha=0.8)
    ax.set_xlabel("Importance"); ax.set_title("What Drives Signing Decisions")
    
    # Audit summary
    ax = axes[1][0]
    risk_labels = ['0%', '1%', '5%', '10%', '20%']
    auto_counts = [results[k]['auto_sign'] for k in results.keys()]
    review_counts = [results[k]['review'] for k in results.keys()]
    x = np.arange(len(risk_labels))
    ax.bar(x - 0.2, auto_counts, 0.4, label='Auto-Sign', color=C["green"], alpha=0.8)
    ax.bar(x + 0.2, review_counts, 0.4, label='Review', color=C["orange"], alpha=0.8)
    ax.set_xticks(x); ax.set_xticklabels(risk_labels)
    ax.set_ylabel("Documents"); ax.set_title("Auto-Sign vs Review")
    ax.legend(); ax.grid(True, alpha=0.2, axis='y')
    
    # Decision chain
    ax = axes[1][1]
    ax.axis('off')
    ax.text(0.5, 0.9, 'Decision Audit Chain', fontsize=12, ha='center', color=C["white"], fontweight='bold')
    chain = [
        "1. Document arrives",
        "2. Nutrient extracts fields",
        "3. Features computed (5 signals)",
        "4. Logistic regression scores",
        "5. Risk budget selects threshold",
        "6. Score >= threshold → AUTO-SIGN",
        "7. Score < threshold → REVIEW",
        "8. SignatureGate enforces",
        "9. Foxit MCP (reversible)",
        "10. Foxit eSign (irreversible)",
    ]
    for i, step in enumerate(chain):
        ax.text(0.1, 0.8 - i*0.08, step, fontsize=9, color=C["cyan"])
    
    plt.tight_layout()
    fig.savefig(f'{OUTPUT_DIR}/optimal_derivation.png', bbox_inches='tight', facecolor='#0d1117')
    plt.close(fig)
    print(f"  Saved: {OUTPUT_DIR}/optimal_derivation.png")
    
    # Summary
    print(f"\n  {'='*60}")
    print(f"  OPTIMAL RISK BUDGETS")
    print(f"  {'='*60}")
    print(f"  {'Budget':>8s}  {'Threshold':>9s}  {'Auto-Sign':>10s}  {'Review':>8s}")
    print(f"  {'-'*8}  {'-'*9}  {'-'*10}  {'-'*8}")
    for k, v in results.items():
        print(f"  {k:>8s}  {v['threshold']:9.3f}  {v['coverage']:9.1%}  {v['review']:8d}")
    
    print(f"\n  Feature importance:")
    for feat, imp in sorted(importance.items(), key=lambda x: abs(x[1]), reverse=True):
        print(f"    {feat:20s} {imp:+.3f}")

def main():
    docs = load_data()
    results, importance = derive_optimal(docs)
    plot_derivation(results, importance)

if __name__ == '__main__':
    main()
