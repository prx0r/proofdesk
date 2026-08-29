#!/usr/bin/env python3
"""ML Optimization Procedure — Cogym-style.

Step 1: Create benchmark with binary labels (1=sign, 0=review)
Step 2: Extract features from all documents
Step 3: Split train/test
Step 4: Optimize on train (evolution + conformal)
Step 5: Test on unseen test set
Step 6: Measure generalization
"""
import asyncio, os, sys, glob, json, numpy as np, random, time
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import cross_val_score

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
# NUTRIENT_API_KEY must be set in env
from src.models.domain import Document
from src.providers.nutrient import extract_from_document

# ─── Step 1: Create Benchmark ────────────────────────────────────────

def load_benchmark():
    """Load all PDFs with binary labels."""
    pdfs = []
    for p in glob.glob('../data/test_pdfs/*.pdf'):
        name = os.path.basename(p)
        gt = 1 if name in [
            'procurement_01_request.pdf', 'procurement_02_quote.pdf',
            'procurement_03_insurance.pdf', 'procurement_04_security.pdf',
            'invoice.pdf', 'invoice_01_vendor_invoice.pdf',
            'vendor_quote.pdf', 'insurance_certificate.pdf',
            'trade_01_invoice.pdf', 'trade_03_certificate_origin.pdf',
            'security_questionnaire.pdf', 'procurement_request.pdf'
        ] else 0
        pdfs.append({'path': p, 'name': name, 'label': gt, 'source': 'proofdesk'})
    
    for p in glob.glob('../data/real_datasets/zugferd/ZUGFeRDv2/correct/**/*.pdf', recursive=True):
        pdfs.append({'path': p, 'name': os.path.basename(p), 'label': 1, 'source': 'zugferd'})
    
    return pdfs

# ─── Step 2: Extract Features ────────────────────────────────────────

def extract_features(doc, facts):
    """Extract 10 features from document."""
    data_acc = sum(f.confidence for f in facts)/len(facts) if facts else 0
    n_fields = len(facts)
    min_conf = min(f.confidence for f in facts) if facts else 0
    max_conf = max(f.confidence for f in facts) if facts else 0
    
    name = doc['name'].lower()
    return [
        data_acc,           # 0: data accuracy
        n_fields / 10,      # 1: field count (normalized)
        min_conf,           # 2: min confidence
        max_conf,           # 3: max confidence
        1 if 'procurement' in name else 0,  # 4: is_procurement
        1 if 'invoice' in name else 0,      # 5: is_invoice
        1 if 'kyc' in name or 'license' in name else 0,  # 6: is_kyc
        1 if 'mortgage' in name else 0,     # 7: is_mortgage
        1 if 'trade' in name else 0,        # 8: is_trade
        1 if 'korrektur' in name else 0,    # 9: is_corrected
    ]

# ─── Step 3: Train/Test Split ────────────────────────────────────────

def split_data(features, labels, test_ratio=0.3, seed=42):
    """Split into train/test."""
    rng = random.Random(seed)
    indices = list(range(len(features)))
    rng.shuffle(indices)
    split = int(len(indices) * (1 - test_ratio))
    
    train_idx = indices[:split]
    test_idx = indices[split:]
    
    return (
        np.array([features[i] for i in train_idx]),
        np.array([labels[i] for i in train_idx]),
        np.array([features[i] for i in test_idx]),
        np.array([labels[i] for i in test_idx]),
    )

# ─── Step 4: Optimize ────────────────────────────────────────────────

def optimize_thresholds(X_train, y_train, n_iter=100):
    """Cogym-style optimization: find optimal threshold per feature."""
    best_tau = 0.5
    best_acc = 0
    
    # Fit logistic regression
    lr = LogisticRegression(C=1.0, max_iter=1000)
    lr.fit(X_train, y_train)
    
    # Get predicted probabilities
    probs = lr.predict_proba(X_train)[:, 1]
    
    # Optimize threshold
    for tau in np.linspace(0.3, 0.9, 50):
        predictions = (probs >= tau).astype(int)
        acc = np.mean(predictions == y_train)
        if acc > best_acc:
            best_acc = acc
            best_tau = tau
    
    return lr, best_tau, best_acc

# ─── Step 5: Evaluate ────────────────────────────────────────────────

def evaluate(X_test, y_test, lr, tau):
    """Evaluate on test set."""
    probs = lr.predict_proba(X_test)[:, 1]
    predictions = (probs >= tau).astype(int)
    
    accuracy = np.mean(predictions == y_test)
    n_sign = np.sum(predictions == 1)
    n_review = np.sum(predictions == 0)
    fp = np.sum((predictions == 1) & (y_test == 0))
    fn = np.sum((predictions == 0) & (y_test == 1))
    
    return {
        'accuracy': accuracy,
        'n_sign': int(n_sign),
        'n_review': int(n_review),
        'fp': int(fp),
        'fn': int(fn),
        'threshold': tau,
    }

# ─── Main ────────────────────────────────────────────────────────────

async def run():
    print('='*70)
    print('  ML OPTIMIZATION PROCEDURE')
    print('='*70)
    
    # Step 1: Load benchmark
    print('\n[1/6] Loading benchmark...')
    pdfs = load_benchmark()
    print(f'  {len(pdfs)} documents: {sum(1 for p in pdfs if p["label"]==1)} safe, {sum(1 for p in pdfs if p["label"]==0)} review')
    
    # Step 2: Extract features
    print('\n[2/6] Extracting features...')
    features = []
    labels = []
    for doc in pdfs:
        d = Document(doc_id='x', case_id='x', filename=doc['name'], content_type='application/pdf', raw_text='')
        with open(doc['path'], 'rb') as f: d.raw_bytes = f.read()
        try:
            facts = await extract_from_document(d)
            feat = extract_features(doc, facts)
            features.append(feat)
            labels.append(doc['label'])
        except: pass
    
    features = np.array(features)
    labels = np.array(labels)
    print(f'  {len(features)} features extracted ({features.shape[1]} dimensions)')
    
    # Step 3: Split
    print('\n[3/6] Splitting train/test...')
    X_train, y_train, X_test, y_test = split_data(features, labels)
    print(f'  Train: {len(X_train)}, Test: {len(X_test)}')
    
    # Step 4: Optimize
    print('\n[4/6] Optimizing thresholds...')
    lr, best_tau, train_acc = optimize_thresholds(X_train, y_train)
    print(f'  Train accuracy: {train_acc:.1%}')
    print(f'  Optimal threshold: {best_tau:.3f}')
    print(f'  Model coefficients: {lr.coef_[0].round(3)}')
    
    # Step 5: Evaluate on test
    print('\n[5/6] Testing on UNSEEN test set...')
    test_results = evaluate(X_test, y_test, lr, best_tau)
    print(f'  Test accuracy: {test_results["accuracy"]:.1%}')
    print(f'  Signed: {test_results["n_sign"]}, Reviewed: {test_results["n_review"]}')
    print(f'  FP: {test_results["fp"]}, FN: {test_results["fn"]}')
    print(f'  Train-Test gap: {train_acc - test_results["accuracy"]:.1%}')
    
    # Step 6: Cross-validation
    print('\n[6/6] Cross-validation...')
    cv_scores = cross_val_score(lr, features, labels, cv=5, scoring='accuracy')
    print(f'  5-fold CV: {cv_scores.mean():.1%} ± {cv_scores.std():.1%}')
    
    # Summary
    print(f'\n{"="*70}')
    print(f'  SUMMARY')
    print(f'{"="*70}')
    print(f'  Dataset: {len(features)} documents')
    print(f'  Train: {train_acc:.1%} ({len(X_train)} docs)')
    print(f'  Test: {test_results["accuracy"]:.1%} ({len(X_test)} docs)')
    print(f'  CV: {cv_scores.mean():.1%} ± {cv_scores.std():.1%}')
    print(f'  Gap: {train_acc - test_results["accuracy"]:.1%}')
    print(f'  Threshold: {best_tau:.3f}')
    
    # Feature importance
    print(f'\n  Feature importance (logistic regression):')
    feature_names = ['data_accuracy', 'n_fields', 'min_conf', 'max_conf',
                     'is_procurement', 'is_invoice', 'is_kyc', 'is_mortgage', 'is_trade', 'is_corrected']
    for name, coef in sorted(zip(feature_names, lr.coef_[0]), key=lambda x: abs(x[1]), reverse=True):
        print(f'    {name:20s} {coef:+.3f}')

asyncio.run(run())
