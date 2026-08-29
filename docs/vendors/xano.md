# Xano Developer MCP + CLI

Source: https://docs.xano.com/developer-mcp/get-started

---

## Developer MCP (docs + validation, no auth needed)

**Install:**
```bash
npm install -g @xano/developer-mcp
# or
npx -y @xano/developer-mcp
```

**Tools (7):**
| Tool | Purpose |
|------|---------|
| `xano_validate_xanoscript` | Validate XanoScript code for syntax errors |
| `xano_xanoscript_docs` | Context-aware XanoScript language docs |
| `xano_meta_api_docs` | Meta API documentation (tables, functions, APIs, tasks, agents, etc.) |
| `xano_cli_docs` | CLI documentation for local dev |
| `xano_knowledge_get` | Retrieve knowledge base entries |
| `xano_knowledge_list` | List available knowledge |
| `xano_version` | Package version |

**Meta API topics:** table, api, function, task, agent, tool, mcp_server, middleware, branch, realtime, file, history, workflows

**CLI topics:** start, auth, profile, workspace, sandbox, branch, function, release, tenant, unit_test, workflow_test, platform, static_host, update, integration

**No authentication required** — runs locally, serves docs only.

## Xano CLI (workspace management, needs auth)

**Install:**
```bash
npm install -g @xano/cli
```

**Setup:**
```bash
xano login          # browser OAuth
xano profile list   # list profiles
```

**Key commands:**
```bash
xano workspace list          # list workspaces
xano workspace pull <id>     # pull workspace code locally
xano workspace push <id>     # push local changes
xano branch list             # list branches
xano branch switch <name>    # switch branch
xano function list           # list functions
xano function get <id>       # get function details
```

**Sandbox:** Auto-provisioned dev environment (free-tier friendly)

## Skills

Two agent skills available:
- `xano-init` — guided workspace setup
- `xanoscript-docs-expert` — deep XanoScript reference

```bash
npx skills add xano-inc/xano-developer-mcp -s xano-init -a claude-code -g
```

## Hackathon Notes

Xano track: "must use Xano as the backend in a meaningful way"

For ProofDesk:
- Xano could host cases, approvals, audit events
- Use Meta API for CRUD on tables
- Use CLI for workspace management
- Register at https://go.xano.co/devpost-challenge for free instance
