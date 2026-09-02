"""Headless inspection — drives the exact flow the dashboard performs.

Upload → staged live run → facts → checks → route → human → sign → seal → proof.
"""
import sys, json
import httpx

BASE = "http://127.0.0.1:3799"
c = httpx.Client(timeout=90)


def main(pdf_paths):
    ok = True

    # 1 ── upload real PDFs (judge flow)
    files = [("files", (p.split("/")[-1], open(p, "rb"), "application/pdf")) for p in pdf_paths]
    r = c.post(f"{BASE}/v1/cases/upload", files=files).json()
    cid = r["case_id"]
    print("══ 1 UPLOAD ══")
    for d in r["documents"]:
        print(f"   {d['filename']} {d['bytes']}B → {d['doc_id']}")

    # 2 ── staged live run
    print("══ 2 LIVE STAGES ══")
    for st in ["INGESTED", "EXTRACTED", "RECONCILED", "CHECKED"]:
        s = c.post(f"{BASE}/v1/cases/{cid}/run", json={"stop_after": st}).json()["state"]
        print(f"   {st:12s} -> {s}")

    # 3 ── facts
    print("══ 3 FACTS ══")
    facts = c.get(f"{BASE}/v1/cases/{cid}/facts").json()["facts"]
    print(f"   {len(facts)} extracted")
    for x in facts[:8]:
        conf = x.get("confidence") or 0
        print(f"   [{conf:>4.0%}] {x['field']:38s} = {str(x['value_normalized'])[:28]:28s} doc...{x['doc_id'][-6:]} p.{x.get('page')}")
    if not facts:
        ok = False

    # 4 ── checks + route to terminal review state
    print("══ 4 CHECKS ══")
    assertions = c.get(f"{BASE}/v1/cases/{cid}/assertions").json()["assertions"]
    fails = [a for a in assertions if a["result"] == "FAIL"]
    print(f"   {len(assertions)} assertions, {len(fails)} FAIL")
    for a in fails:
        print(f"   X {a['predicate']} -- {a['detail'][:70]}")
    state = c.post(f"{BASE}/v1/cases/{cid}/run", json={}).json().get("state")
    print(f"   routed -> {state}")

    # 5 ── human + completion
    print("══ 5 HUMAN + COMPLETION ══")
    if fails:
        r = c.post(f"{BASE}/v1/cases/{cid}/resolve", json={
            "assertion_id": fails[0]["assertion_id"],
            "decision": "CONDITIONAL_ACCEPT",
            "reason": "Human reviewed source evidence; renewed cert required",
            "actor_id": "reviewer"}).json()
        print(f"   resolve -> {r.get('state')}")
    for step in ["approve", "generate", "prepare"]:
        code = c.post(f"{BASE}/v1/cases/{cid}/{step}").status_code
        print(f"   {step:20s} HTTP {code}")
        ok &= code == 200
    code = c.post(f"{BASE}/v1/cases/{cid}/signature-request",
                  json={"signer": "judge@example.com"}).status_code
    print(f"   signature-request    HTTP {code}"); ok &= code == 200
    code = c.post(f"{BASE}/v1/cases/{cid}/sign").status_code
    print(f"   sign                 HTTP {code}"); ok &= code == 200

    # 6 ── seal + merkle
    print("══ 6 SEAL + MERKLE ══")
    seal = c.get(f"{BASE}/v1/audit/seal").json()
    print(f"   epoch {seal['epoch_id']}: {seal['events']} events, root {seal['root'][:24]}...")
    proof = c.get(f"{BASE}/v1/audit/proof/0").json()
    print(f"   inclusion proof seq=0 verified: {proof['verified']}")
    h = c.get(f"{BASE}/health").json()
    print(f"   global chain integrity: {h['audit']['chain_integrity']}")
    ok &= bool(h["audit"]["chain_integrity"])

    # 7 ── final
    print("══ 7 FINAL ══")
    case = c.get(f"{BASE}/v1/cases/{cid}").json()
    receipt = c.get(f"{BASE}/v1/cases/{cid}/receipt").json()
    memo = receipt.get("generated_content", "")
    print(f"   state={case['state']} band={case['risk_band']} conf={case['signing_confidence']}")
    print(f"   record={case['record_hash']}")
    print(f"   memo_len={len(memo)} status_rendered={'APPROVED' in memo}")
    dash = c.get(f"{BASE}/")
    print(f"   dashboard served: HTTP {dash.status_code}, {len(dash.text)//1024}KB")

    print()
    print("HEADLESS INSPECTION:", "ALL GREEN" if ok else "ISSUES FOUND")
    return ok


if __name__ == "__main__":
    paths = sys.argv[1:] or [
        "fixtures/demo/vendor_quote.pdf",
        "fixtures/demo/procurement_request.pdf",
        "fixtures/demo/insurance_certificate.pdf",
        "fixtures/demo/security_questionnaire.pdf",
    ]
    sys.exit(0 if main(paths) else 1)
