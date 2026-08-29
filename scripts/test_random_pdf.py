"""Random-PDF dashboard flow inspection — upload, staged run, facts, trace."""
import sys
import httpx

BASE = "http://127.0.0.1:3799"
c = httpx.Client(timeout=90)


def main(pdf_path):
    # upload random pdf
    r = c.post(f"{BASE}/v1/cases/upload",
               files={"files": (pdf_path.split("/")[-1], open(pdf_path, "rb"), "application/pdf")}).json()
    cid = r["case_id"]
    print(f"case: {cid}  ({pdf_path.split('/')[-1]})")

    for st in ["INGESTED", "EXTRACTED", "RECONCILED", "CHECKED"]:
        s = c.post(f"{BASE}/v1/cases/{cid}/run", json={"stop_after": st}).json()["state"]
        print(f"  stage {st} → {s}")

    print("\n── FACTS ──")
    facts = c.get(f"{BASE}/v1/cases/{cid}/facts").json()["facts"]
    print(f"  {len(facts)} facts:")
    for x in facts[:6]:
        conf = x.get("confidence") or 0
        val = str(x.get("value_normalized"))[:40]
        print(f"    [{conf:.0%}] {x['field']} = {val}")

    print("\n── VENDOR API TRACE ──")
    calls = c.get(f"{BASE}/v1/cases/{cid}/trace").json()["calls"]
    print(f"  {len(calls)} vendor calls traced:")
    for i, call in enumerate(calls):
        ok = (call.get("status") or 0) < 400
        mark = "OK" if ok else "FAIL"
        print(f"    [{mark}] {call['provider']} | {call['operation']} | "
              f"status={call['status']} | {call['duration_ms']}ms")
        req = call.get("request") or {}
        if isinstance(req, dict):
            for k in list(req.keys())[:4]:
                print(f"        req.{k}: {str(req[k])[:70]}")

    print("\n── TRACE PANEL DATA STRUCTURE OK ──" if calls else "── NO CALLS TRACED ──")
    return len(calls) > 0


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/proofdesk/ocr_000.pdf"
    sys.exit(0 if main(path) else 1)
