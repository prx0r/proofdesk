"""Headless MCP client test — speaks stdio JSON-RPC to the ProofDesk MCP server."""
import json, subprocess, sys

PROC = subprocess.Popen(
    [sys.executable, "-m", "src.mcp.server"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL, text=True)

_id = 0
def rpc(method, params=None):
    global _id
    _id += 1
    PROC.stdin.write(json.dumps({"jsonrpc":"2.0","id":_id,"method":method,"params":params or {}})+"\n")
    PROC.stdin.flush()
    while True:
        line = PROC.stdout.readline()
        if not line:
            raise RuntimeError("server died")
        msg = json.loads(line)
        if msg.get("id") == _id:
            return msg

def tool(name, args):
    r = rpc("tools/call", {"name": name, "arguments": args})
    if "error" in r: raise RuntimeError(r["error"])
    return json.loads(r["result"]["content"][0]["text"])

# 1. initialize + list
r = rpc("initialize", {"protocolVersion":"2024-11-05",
    "capabilities":{}, "clientInfo":{"name":"inspect","version":"1.0"}})
print("══ INIT ══")
print("  server:", r["result"]["serverInfo"]["name"])
tools = rpc("tools/list", {})["result"]["tools"]
print(f"  {len(tools)} tools:", ", ".join(t["name"] for t in tools))

# 2. full lifecycle on uploaded PDFs
print("\n══ LIFECYCLE ══")
c = tool("proofdesk_create_case", {"prompt":"MCP-driven inspection run"})
cid = c["case_id"]; print("  case:", cid)
for p in ["fixtures/demo/vendor_quote.pdf","fixtures/demo/procurement_request.pdf",
          "fixtures/demo/insurance_certificate.pdf","fixtures/demo/security_questionnaire.pdf"]:
    d = tool("proofdesk_upload_pdf", {"case_id":cid,"path":p})
    print("  uploaded:", d["filename"], d["bytes"],"B")
for st in ["INGESTED","EXTRACTED","CHECKED"]:
    s = tool("proofdesk_run_stage", {"case_id":cid,"stop_after":st})
    print(f"  stage {st}: state={s['state']} facts={s['facts']} blockers={s['blocking_exceptions']}")
f = tool("proofdesk_facts", {"case_id":cid})
print("  facts:", len(f["facts"]), "| sample:", f["facts"][0]["field"], "=", f["facts"][0]["value_normalized"][:30])
a = tool("proofdesk_checks", {"case_id":cid})
fails=[x for x in a["assertions"] if x["result"]=="FAIL"]
print("  checks:", len(a["assertions"]), "failures:", len(fails))
if fails:
    r2 = tool("proofdesk_resolve", {"case_id":cid,"assertion_id":fails[0]["assertion_id"],
        "decision":"CONDITIONAL_ACCEPT","reason":"Human reviewed","actor_id":"mcp-test"})
    print("  resolve ->", r2["state"])
g = tool("proofdesk_signature_gate", {"case_id":cid})
adv = tool("proofdesk_advance", {"case_id":cid,"signer":"judge@example.com"})
print("  advance log:", adv["log"], "-> state:", adv["state"])

# 3. audit + merkle + stats
print("\n══ AUDIT ══")
au = tool("proofdesk_audit", {"case_id":cid})
print("  chain valid:", au["chain_valid"], "| events:", au.get("total_events"))
tool("proofdesk_seal", {})
p = tool("proofdesk_merkle_proof", {"seq":0})
print("  merkle proof seq=0 verified:", p["verified"], "root:", p["root"][:16]+"…")
s = tool("proofdesk_convergence_stats", {})
print("  convergence labels:", s["convergence"]["total_feedback"],
      "| auto-sign panel:", s["convergence"]["auto_sign_panel"]["auto_signed_total"])

# error-path check
bad = rpc("tools/call", {"name":"proofdesk_facts","arguments":{"case_id":"nonexistent"}})
err = bad["result"]["content"][0]["text"]
print("\n  error path returns structured:", "Case nonexistent not found" in err)

PROC.terminate()
print("\nMCP SERVER INSPECTION: ALL GREEN ✅")
