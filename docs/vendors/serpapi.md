# SerpApi MCP Server

Source: https://serpapi.com/blog/introducing-serpapis-mcp-server/

---

## Setup

**Remote (easiest):**
```
https://mcp.serpapi.com/<API_KEY>/mcp
```

**Self-hosted:**
```bash
git clone https://github.com/serpapi/serpapi-mcp.git
cd serpapi-mcp && uv sync
echo "SERPAPI_API_KEY=your_key" > .env
uv run src/server.py
```

## Tool: `search`

Unified search across 100+ engines. Supports Google, Bing, Yahoo, DuckDuckGo, YouTube, eBay, Walmart, Amazon, etc.

**Parameters:**
```json
{
  "params": {
    "engine": "google",
    "q": "search query",
    "location": "Austin, Texas",
    "hl": "en",
    "gl": "us"
  },
  "mode": "complete"  // or "clean" for normalized output
}
```

**Result types:** Answer boxes, organic results, news, images, shopping, knowledge graph.

**Modes:**
- `complete` — full raw JSON
- `clean` — normalized fields (title, snippet, link)

## Resources

- `serpapi://engines` — list all available engines
- `serpapi://engines/{engine_name}` — per-engine parameters

## Key Features

- Multi-engine: one tool covers dozens of search providers
- Structured JSON: answer boxes, knowledge graphs, calculations
- Error handling + retry logic built-in
- Free plan: 250 searches/month

## Engines

Google (full + light), Bing, Yahoo, DuckDuckGo, Yandex, Baidu, YouTube, eBay, Walmart, Amazon, Apple Maps, Naver, Brave, and more.

See full list: https://serpapi.com/search-engine-apis
