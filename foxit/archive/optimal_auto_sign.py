#!/usr/bin/env python3
"""Derive optimal auto-sign levels per document type and risk level."""

import os, sys, json
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))

OUTPUT_DIR = "/tmp/proofdesk/optimal"
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
        })
    return docs

def derive_optimal(docs, risk_budgets=[0.0, 0.01, 0.05, 0.10, 0.20]):
    """Derive optimal auto-sign level for each risk budget."""
    from sklearn.linear_model import LogisticRegression
    
    X = np.array([d['features'] for d in docs])
    y = np.array([d['label'] for d in docs])
    
    lr = LogisticRegression(C=1.0, max_iter=1000)
    lr.fit(X, y)
    probs = lr.predict_proba(X)[:, 1]
    
    results = {}
    for alpha in risk_budgets:
        sorted_probs = np.sort(probs)
        idx = int(np.ceil((1 - alpha) * (1 + 1/len(sorted_probs)) * len(sorted_probs)))
        tau = sorted_probs[min(idx, len(sorted_probs)-1)]
        preds = (probs >= tau).astype(int)
        coverage = preds.mean()
        fp = int(np.sum((preds == 1) & (y == 0)))
        
        results[f"{alpha:.0%}"] = {
            'threshold': float(tau),
            'coverage': float(coverage),
            'auto_sign': int(preds.sum()),
            'review': int((~preds.astype(bool)).sum()),
            'false_signs': fp,
        }
    
    return results

def plot_optimal(results):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Optimal Auto-Sign Levels by Risk Budget", fontsize=14, fontweight="bold", color=C["white"])
    
    alphas = [float(k.replace('%',''))/100 for k in results.keys()]
    coverages = [results[k]['coverage']*100 for k in results.keys()]
    thresholds = [results[k]['threshold'] for k in results.keys()]
    
    # Coverage
    ax = axes[0]
    bars = ax.bar([f"{a:.0%}" for a in alphas], coverages, color=[C["green"] if a <= 0.05 else C["orange"] if a <= 0.10 else C["red"] for a in alphas], alpha=0.8, edgecolor='white', linewidth=0.3)
    for bar, val in zip(bars, coverages):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.5, f"{val:.0f}%", ha='center', fontsize=10, color=C["white"])
    ax.set_xlabel("Risk Budget (False Sign Rate)")
    ax.set_ylabel("Coverage (% auto-sign)")
    ax.set_title("How Many Docs Can You Auto-Sign?")
    ax.grid(True, alpha=0.2, axis='y')
    
    # Thresholds
    ax = axes[1]
    bars = ax.bar([f"{a:.0%}" for a in alphas], thresholds, color=[C["green"] if a <= 0.05 else C["orange"] if a <= 0.10 else C["red"] for a in alphas], alpha=0.8, edgecolor='white', linewidth=0.3)
    for bar, val in zip(bars, thresholds):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.001, f"{val:.3f}", ha='center', fontsize=10, color=C["white"])
    ax.set_xlabel("Risk Budget (False Sign Rate)")
    ax.set_ylabel("Threshold")
    ax.set_title("Optimal Threshold per Risk Budget")
    ax.grid(True, alpha=0.2, axis='y')
    
    plt.tight_layout()
    fig.savefig(f'{OUTPUT_DIR}/optimal_auto_sign.png', bbox_inches='tight', facecolor='#0d1117')
    plt.close(fig)
    print(f"  Saved: {OUTPUT_DIR}/optimal_auto_sign.png")
    
    print(f"\n  {'='*60}")
    print(f"  OPTIMAL AUTO-SIGN LEVELS")
    print(f"  {'='*60}")
    print(f"  {'Risk Budget':>12s}  {'Threshold':>9s}  {'Auto-Sign':>10s}  {'Review':>8s}  {'False Signs':>11s}")
    print(f"  {'-'*12}  {'-'*9}  {'-'*10}  {'-'*8}  {'-'*11}")
    for k, v in results.items():
        print(f"  {k:>12s}  {v['threshold']:9.3f}  {v['coverage']:9.1%}  {v['review']:8d}  {v['false_signs']:11d}")

def main():
    print("="*60)
    print("  OPTIMAL AUTO-SIGN — Derive Levels per Risk Budget")
    print("="*60)
    
    docs = load_data()
    print(f"Loaded {len(docs)} invoices\n")
    
    results = derive_optimal(docs)
    plot_optimal(results)

if __name__ == '__main__':
    main()
