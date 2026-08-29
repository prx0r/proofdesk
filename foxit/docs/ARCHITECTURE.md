# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    SIGNATUREGATE                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ Document │───▶│ Extract  │───▶│ Score    │              │
│  │ Upload   │    │ (Nutrient)│    │ (CRC)    │              │
│  └──────────┘    └──────────┘    └──────────┘              │
│                                          │                  │
│                                          ▼                  │
│                                    ┌──────────┐            │
│                                    │ Gate     │            │
│                                    │ (5 cond) │            │
│                                    └──────────┘            │
│                                          │                  │
│                          ┌───────────────┼───────────────┐ │
│                          ▼               ▼               ▼ │
│                     ┌────────┐      ┌────────┐      ┌────────┐
│                     │ SIGN   │      │ REVIEW │      │ REFUSE │
│                     └────────┘      └────────┘      └────────┘
│                          │               │               │
│                          ▼               ▼               ▼ │
│                     ┌──────────────────────────────────────┐│
│                     │ Merkle Audit Trail (14 events)       ││
│                     └──────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

1. **Upload** → Document bytes stored, SHA-256 computed
2. **Extract** → Nutrient API returns fields + confidence
3. **Score** → CRC threshold based on risk level
4. **Gate** → 5 conditions checked (blockers, approval, hash, signer, threshold)
5. **Decision** → Sign / Review / Refuse
6. **Audit** → Hash chain + Merkle seal

## Risk Levels

| Level | Threshold | Documents | Strategy |
|-------|-----------|-----------|----------|
| Low | τ=1.000 | Contracts | Sign everything |
| Medium | τ=1.000 | Invoices | Sign almost everything |
| High | τ=0.354 | Fraud transactions | Sign half, review half |

## Features Used

| Feature | Importance | Source |
|---------|------------|--------|
| amount | 0.36 | Transaction amount |
| time_since | 0.26 | Time since last transaction |
| is_night | 0.25 | Night transaction (6pm-6am) |
| deviation | 0.10 | Amount deviation from average |
| count_24h | 0.03 | Transaction count in 24h |

## Audit Trail

Every decision is hash-chained:
```
Event 1: INGESTED → doc_bytes_hash
Event 2: EXTRACTED → field_confidences
Event 3: CHECKED → assertions
Event 4: GATE → threshold_decision
Event 5: RESOLVED → human_judgment
Event 6: APPROVED → record_hash
Event 7: GENERATED → artifact_hash
Event 8: PREPARED → pdf_hash
Event 9: SIGNATURE_REQUESTED → signer
Event 10: SIGNED → signature_hash
Event 11: ARCHIVED → final_hash
```

All events are Merkle-sealed for tamper evidence.
