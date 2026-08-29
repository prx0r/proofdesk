#!/usr/bin/env python3
"""Cogym-style optimization on unseen documents.

Pattern:
1. Split documents into train/test
2. Extract features from all documents
3. Optimize thresholds on train (evolve)
4. Test on unseen test set
5. Measure generalization
"""
import asyncio, os, sys, glob, json, numpy as np, random, time
# NUTRIENT_API_KEY must be set in env
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.models.domain import Document
from src.providers.nutrient import extract_from_document

def load_all():
    pdfs = []
    for p in glob.glob('../data/test_pdfs/*.pdf'):
        pdfs.append({'path': p, 'name': os.path.basename(p), 'gt': 'safe', 'source': 'proofdesk'})
    for p in glob.glob('../data/real_datasets/zugferd/ZUGFeRDv2/correct/**/*.pdf', recursive=True):
        pdfs.append({'path': p, 'name': os.path.basename(p), 'gt': 'safe', 'source': 'zugferd'})
    return pdfs

def extract_features(doc, facts):
    """Extract features for optimization."""
    data_acc = sum(f.confidence for f in facts)/len(facts) if facts else 0
    n_fields = len(facts)
    min_conf = min(f.confidence for f in facts) if facts else 0
    
    # Document type features
    name = doc['name'].lower()
    is_procurement = 1 if 'procurement' in name else 0
    is_invoice = 1 if 'invoice' in name else 0
    is_kyc = 1 if 'kyc' in name or 'license' in name else 0
    is_mortgage = 1 if 'mortgage' in name or 'appraisal' in name else 0
    is_trade = 1 if 'trade' in name else 0
    
    return {
        'data_accuracy': data_acc,
        'n_fields': n_fields,
        'min_confidence': min_conf,
        'is_procurement': is_procurement,
        'is_invoice': is_invoice,
        'is_kyc': is_kyc,
        'is_mortgage': is_mortgage,
        'is_trade': is_trade,
    }

def compute_confidence(features, weights):
    """Compute signing confidence from features and weights."""
    score = (
        weights[0] * features['data_accuracy'] +
        weights[1] * features['min_confidence'] +
        weights[2] * features['n_fields'] / 10 +
        weights[3] * features['is_procurement'] +
        weights[4] * features['is_invoice'] +
        weights[5] * features['is_kyc'] +
        weights[6] * features['is_mortgage'] +
        weights[7] * features['is_trade']
    )
    return max(0.0, min(1.0, score))

def evaluate(features_list, labels, weights, threshold):
    """Evaluate weights and threshold on a set of documents."""
    correct = 0
    for features, gt in zip(features_list, labels):
        sc = compute_confidence(features, weights)
        decision = 'SIGN' if sc >= threshold else 'REVIEW'
        ok = (decision=='SIGN' and gt=='safe') or (decision=='REVIEW' and gt=='review')
        if ok: correct += 1
    return correct / len(labels) if labels else 0

def cogym_optimize(train_features, train_labels, n_generations=50, n_pop=20):
    """Cogym-style evolution to find optimal weights and threshold."""
    rng = np.random.RandomState(42)
    
    # Initialize population
    pop = []
    for _ in range(n_pop):
        weights = rng.uniform(0, 1, 8)
        threshold = rng.uniform(0.5, 0.95)
        pop.append({'weights': weights, 'threshold': threshold, 'fitness': 0})
    
    best_fitness = 0
    best_weights = None
    best_threshold = 0.5
    
    for gen in range(n_generations):
        # Evaluate each individual
        for ind in pop:
            ind['fitness'] = evaluate(train_features, train_labels, ind['weights'], ind['threshold'])
        
        # Sort by fitness
        pop.sort(key=lambda x: x['fitness'], reverse=True)
        
        # Track best
        if pop[0]['fitness'] > best_fitness:
            best_fitness = pop[0]['fitness']
            best_weights = pop[0]['weights'].copy()
            best_threshold = pop[0]['threshold']
        
        if gen % 10 == 0:
            print(f'  Gen {gen:3d}: best_fitness={pop[0]["fitness"]:.3f}  threshold={pop[0]["threshold"]:.3f}')
        
        # Selection + mutation
        new_pop = pop[:5]  # Keep top 5
        while len(new_pop) < n_pop:
            parent = rng.choice(pop[:10])
            child_weights = parent['weights'] + rng.normal(0, 0.1, 8)
            child_threshold = parent['threshold'] + rng.normal(0, 0.05)
            child_threshold = np.clip(child_threshold, 0.3, 0.99)
            new_pop.append({'weights': child_weights, 'threshold': child_threshold, 'fitness': 0})
        
        pop = new_pop
    
    return best_weights, best_threshold, best_fitness

async def run():
    print('='*70)
    print('  COGYM OPTIMIZATION — Unseen Documents')
    print('='*70)
    
    # Load documents
    pdfs = load_all()
    print(f'\n[1/5] Loading {len(pdfs)} documents...')
    
    # Extract features from ALL documents
    print(f'[2/5] Extracting features...')
    all_features = []
    all_labels = []
    
    for doc in pdfs:
        d = Document(doc_id='x', case_id='x', filename=doc['name'], content_type='application/pdf', raw_text='')
        with open(doc['path'], 'rb') as f: d.raw_bytes = f.read()
        try:
            facts = await extract_from_document(d)
            features = extract_features(doc, facts)
            all_features.append(features)
            all_labels.append(doc)
        except:
            pass
    
    print(f'  Extracted features for {len(all_features)} documents')
    
    # Split train/test
    print(f'[3/5] Splitting train/test...')
    rng = random.Random(42)
    indices = list(range(len(all_features)))
    rng.shuffle(indices)
    split = int(len(indices) * 0.7)
    
    train_idx = indices[:split]
    test_idx = indices[split:]
    
    train_features = [all_features[i] for i in train_idx]
    train_labels = [all_labels[i] for i in train_idx]
    test_features = [all_features[i] for i in test_idx]
    test_labels = [all_labels[i] for i in test_idx]
    
    print(f'  Train: {len(train_features)}, Test: {len(test_features)}')
    
    # Optimize on train
    print(f'[4/5] Optimizing on train set...')
    best_weights, best_threshold, train_fitness = cogym_optimize(train_features, train_labels)
    print(f'  Train accuracy: {train_fitness:.1%}')
    print(f'  Optimal threshold: {best_threshold:.3f}')
    print(f'  Weights: {best_weights.round(3)}')
    
    # Test on unseen
    print(f'[5/5] Testing on UNSEEN test set...')
    test_accuracy = evaluate(test_features, test_labels, best_weights, best_threshold)
    print(f'  Test accuracy: {test_accuracy:.1%}')
    print(f'  Train-Test gap: {train_fitness - test_accuracy:.1%}')
    
    # Per-document details on test set
    print(f'\n  Test set details:')
    for i, (features, doc) in enumerate(zip(test_features, test_labels)):
        sc = compute_confidence(features, best_weights)
        decision = 'SIGN' if sc >= best_threshold else 'REVIEW'
        ok = (decision=='SIGN' and doc['gt']=='safe') or (decision=='REVIEW' and doc['gt']=='review')
        print(f'    {doc["name"]:50s}  sc={sc:.3f}  {decision:6s}  gt={doc["gt"]:6s}  {"OK" if ok else "XX"}')
    
    print(f'\n  Summary:')
    print(f'    Train: {train_fitness:.1%} ({len(train_features)} docs)')
    print(f'    Test:  {test_accuracy:.1%} ({len(test_features)} docs)')
    print(f'    Gap:   {train_fitness - test_accuracy:.1%}')

asyncio.run(run())
