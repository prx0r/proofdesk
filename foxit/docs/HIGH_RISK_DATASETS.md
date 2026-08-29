# Complete High-Risk Dataset Reference (Updated)

## All Datasets with Fraud Labels

### Insurance Claims (8,000+ docs)
| Dataset | Size | Fraud Labels | Source |
|---------|------|--------------|--------|
| INS-007 | 5,000 | 12 fraud types, 40+ red flags | HuggingFace |
| Vehicle Claims | 1,000 | Binary fraud | Kaggle |
| Insurance Claims | 1,000 | Binary fraud | Kaggle |
| NHIS Healthcare | 1,000 | Fraud types | Kaggle |
| CMS Medicare | 90M+ | Provider fraud | GitHub |

### Contracts (4,000+ docs)
| Dataset | Size | Fraud Labels | Source |
|---------|------|--------------|--------|
| CUAD | 510 | 41 clause types | HuggingFace |
| ContractNER | 3,240 | 18 entity types | HuggingFace |
| Lease Disputes | 100 | Dispute types | HuggingFace |
| Employment Disputes | 100 | Dispute types | HuggingFace |

### Securities/Fraud (10,000+ docs)
| Dataset | Size | Fraud Labels | Source |
|---------|------|--------------|--------|
| 10K Fraud | 10,000+ | AAER fraud labels | Zenodo |
| Financial Statement Fraud | 1,850 | 414 fraud cases | GitHub |
| SEC XBRL | 192M+ data points | Restatement detection | GitHub |

### KYC/Identity (8,000+ docs)
| Dataset | Size | Fraud Labels | Source |
|---------|------|--------------|--------|
| AIForge-Doc | 4,061 | AI-forged docs | HuggingFace |
| Doc-Sentry | 26 | Tampering | GitHub |
| SDB-26 | 4,061 | Synthetic fraud | GitHub |

### Mortgage (5M+ docs)
| Dataset | Size | Fraud Labels | Source |
|---------|------|--------------|--------|
| HMDA | 5M+ | Denial reasons | Kaggle |
| CMBS Loans | 2,313 | Loan data | HuggingFace |

### Tax (10,000+ docs)
| Dataset | Size | Fraud Labels | Source |
|---------|------|--------------|--------|
| Tax Fraud XAI | Synthetic | Fraud labels | GitHub |
| 1099 Reconciliation | N/A | Reconciliation | GitHub |

### Bank (1,000+ docs)
| Dataset | Size | Fraud Labels | Source |
|---------|------|--------------|--------|
| Bank Account Fraud | Large | Tabular fraud | Kaggle |
| Bank Statement | 41 | Parsing challenges | GitHub |

## Total: 5.2M+ documents with fraud labels

## What We're Missing
- Medical records (HIPAA restricted)
- Some tax forms (IRS restrictions)

## Priority for Download
1. INS-007 (insurance fraud, 12 types)
2. CUAD (contracts, 41 clause types)
3. 10K Fraud (securities, AAER labels)
4. AIForge-Doc (AI-forged docs)
5. Bank Account Fraud (tabular fraud)
