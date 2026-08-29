#!/usr/bin/env python3
"""False Sign Tradeoff — show what 0%, 1%, 5%, 10%, 20% costs in coverage."""

import os, sys, json, time
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))

OUTPUT_DIR = "/tmp/proofdesk/tradeoff"
os.makedirs(OUTPUT_DIR, exist_ok=True)

plt.rcParams.update({
    "figure.facecolor": "#0d1117", "axes.facecolor": "#161b22",
    "axes.edgecolor": "#30363d", "axes.labelcolor": "#c9d1d9",
    "text.color": "#c9d1d9", "xtick.color": "#8b949e",
    "ytick.color": "#8b949e", "grid.color": "#21262d",
    "grid.alpha": 0.6, "figure.dpi": 150, "font.size": 11,
})
C = {"blue": "#58a6ff", "green": "#3fb950", "red": "#f85149",
     "orange": "#d29922", "purple": "#bc8cff", "cyan": "#39d2c0", "white": "#c9d1d9"}

def load_data():
    """Load InvoiceBenchmark with real fraud labels."""
    from datasets import load_dataset
    ds = load_dataset('jngb-labs/InvoiceBenchmark', split='test', token='os.environ.get('HF_TOKEN', '')')
    
    docs = []
    for item in ds:
        c = float(item['correct_total'])
        r = float(item['rendered_total'])
        is_correct = abs(c - r) < 0.01
        docs.append({
            'features': [c/10000, r/10000, abs(c-r)/1000, 1 if item['has_discount'] else 0, 1 if item['edge_case'] else 0],
            'label': 1 if is_correct else 0,  # 1=safe, 0=fraud
            'doc_type': 'invoice',
        })
    return docs

def compute_tradeoff(docs, alphas=[0.0, 0.01, 0.05, 0.10, 0.20]):
    """Compute coverage at each false sign rate."""
    from sklearn.linear_model import LogisticRegression
    
    X = np.array([d['features'] for d in docs])
    y = np.array([d['label'] for d in docs])
    
    lr = LogisticRegression(C=1.0, max_iter=1000)
    lr.fit(X, y)
    probs = lr.predict_proba(X)[:, 1]
    
    results = {}
    for alpha in alphas:
        # Find threshold via conformal quantile
        sorted_probs = np.sort(probs)
        idx = int(np.ceil((1 - alpha) * (1 + 1/len(sorted_probs)) * len(sorted_probs)))
        tau = sorted_probs[min(idx, len(sorted_probs)-1)]
        
        # Compute metrics
        preds = (probs >= tau).astype(int)
        coverage = preds.mean()
        fp = np.sum((preds == 1) & (y == 0))
        fpr = fp / max(1, np.sum(y == 0))
        fn = np.sum((preds == 0) & (y == 1))
        fnr = fn / max(1, np.sum(y == 1))
        
        results[f"{alpha:.0%}"] = {
            'alpha': alpha,
            'threshold': float(tau),
            'coverage': float(coverage),
            'fpr': float(fpr),
            'fnr': float(fnr),
            'auto_sign': int(preds.sum()),
            'review': int((~preds.astype(bool)).sum()),
            'false_signs': int(fp),
        }
        
        print(f"  α={alpha:4.0%}:  τ={tau:.3f}  coverage={coverage:.1%}  "
              f"auto_sign={int(preds.sum())}/{len(y)}  false_signs={int(fp)}")
    
    return results

def plot_tradeoff(results):
    """Plot the false sign tradeoff curve."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("False Sign Rate Tradeoff — What 0% Costs", fontsize=14, fontweight="bold", color=C["white"])
    
    alphas = [float(k.replace('%',''))/100 for k in results.keys()]
    coverages = [results[k]['coverage'] for k in results.keys()]
    false_signs = [results[k]['false_signs'] for k in results.keys()]
    thresholds = [results[k]['threshold'] for k in results.keys()]
    
    # Coverage vs False Sign Rate
    ax = axes[0]
    ax.plot([a*100 for a in alphas], [c*100 for c in coverages], 'o-', color=C["cyan"], linewidth=2, markersize=8)
    ax.set_xlabel("False Sign Rate (%)")
    ax.set_ylabel("Coverage (% auto-sign)")
    ax.set_title("Coverage vs False Sign Rate")
    ax.grid(True, alpha=0.2)
    for a, c in zip(alphas, coverages):
        ax.annotate(f"{c:.0%}", (a*100, c*100), textcoords="offset points", xytext=(0,10), ha='center', fontsize=9, color=C["white"])
    
    # Threshold vs False Sign Rate
    ax = axes[1]
    ax.plot([a*100 for a in alphas], thresholds, 's-', color=C["orange"], linewidth=2, markersize=8)
    ax.set_xlabel("False Sign Rate (%)")
    ax.set_ylabel("Threshold")
    ax.set_title("Threshold vs False Sign Rate")
    ax.grid(True, alpha=0.2)
    
    # False signs vs Coverage
    ax = axes[2]
    ax.plot([c*100 for c in coverages], false_signs, 'D-', color=C["purple"], linewidth=2, markersize=8)
    ax.set_xlabel("Coverage (% auto-sign)")
    ax.set_ylabel("False Signs")
    ax.set_title("False Signs vs Coverage")
    ax.grid(True, alpha=0.2)
    
    plt.tight_layout()
    fig.savefig(f'{OUTPUT_DIR}/tradeoff_curve.png', bbox_inches='tight', facecolor='#0d1117')
    plt.close(fig)
    print(f"\n  Saved: {OUTPUT_DIR}/tradeoff_curve.png")
    
    # Summary table
    print(f"\n  {'='*60}")
    print(f"  SUMMARY: What Each False Sign Rate Costs")
    print(f"  {'='*60}")
    print(f"  {'Rate':>6s}  {'Threshold':>9s}  {'Auto-Sign':>10s}  {'Review':>8s}  {'False Signs':>11s}")
    print(f"  {'-'*6}  {'-'*9}  {'-'*10}  {'-'*8}  {'-'*11}")
    for k, v in results.items():
        print(f"  {k:>6s}  {v['threshold']:9.3f}  {v['coverage']:9.1%}  {v['review']:8d}  {v['false_signs']:11d}")

def main():
    print("="*60)
    print("  FALSE SIGN TRADEOFF — What 0% Costs")
    print("="*60)
    
    docs = load_data()
    print(f"Loaded {len(docs)} invoices\n")
    
    results = compute_tradeoff(docs)
    plot_tradeoff(results)

if __name__ == '__main__':
    main()
