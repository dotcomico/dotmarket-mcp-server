# Supermarket MCP Server

Exposes the Supermarket Flask backend as [MCP](https://modelcontextprotocol.io)
tools, so any MCP client (Claude Desktop, the MCP Inspector, and later our
own chatbot agent service) can call backend functionality without knowing
about HTTP, routes, or auth details directly.

## Architecture

```
MCP client (agent/chatbot, or MCP Inspector for manual testing)
        │  MCP protocol (Streamable HTTP — this service is a standalone
        │  process reached by URL, not spawned as a child process)
        ▼
  src/server.py        — tool definitions (schemas + docstrings the
                          LLM reads to decide when/how to call a tool)
        │
        ▼
  src/backend_client.py — thin HTTP wrapper; the ONLY place that knows
                           the backend's base URL and endpoint shapes
        │  HTTP
        ▼
  Flask backend (../backend) — owns all validation, business rules, and
                                 DB access. This server has none of its own.
```

**Why call the backend's REST API instead of the database directly?**
The backend already owns validation, stock rules, and auth (see
`backend/CLAUDE.md`). Reimplementing that here would duplicate business
logic and risk drifting out of sync. Every tool should be a thin
translation: `tool call → HTTP request → backend response → tool result`.

## Tools

| Tool | Backend endpoint | Auth required |
|---|---|---|
| `get_products` | `GET /api/products/` | None (public endpoint) |
| `get_product` | `GET /api/products/<id>` | None (public endpoint) |
| `get_category_tree` | `GET /api/categories/tree` | None (public endpoint) |
| `get_products_by_category` | `GET /api/categories/<slug>/products` | None (public endpoint) |

Only read-only, no-auth tools exist so far, by design — phase 1 is a fully
capable product/category chatbot with no auth. The MCP layer is being
proven out on that before the chatbot/agent service is built on top of it.

### Known gap: auth passthrough

None of the current tools need auth. The next tool that acts *on behalf of a
specific customer* (e.g. adding items to their order) will need their
identity forwarded to the backend's JWT-protected endpoints. That pattern
(how a tool call carries a user's JWT through to `backend_client`) is not
yet designed — decide it before adding such a tool, not while adding it.

### Known gap: no real cart/shopping-list backend support

The backend has no cart/add-item-to-order endpoint today — `POST /api/orders/`
is a one-shot checkout that takes a complete `items` list + address and
immediately decrements stock. There is nothing to call yet for "add one
item to a list I'm building over several chat messages." Do not wire a
tool to `POST /api/orders/` per item — that would create a separate real order
and decrement real stock on every message. Decide the cart model (backend
feature vs. agent-side conversation state, see chat history) before
building that tool.

## Technical decisions

Why each piece of tech is here, what it's *not* (a common confusion point),
and what's still an open choice.

### Already decided

| Choice | Why | Not chosen (and why) |
|---|---|---|
| **MCP (`mcp` / `FastMCP`)** | The protocol layer that lets any MCP client (Claude Desktop, MCP Inspector, a future agent) call backend functionality as typed tools, without client-specific integration glue. `@mcp.tool()` derives the schema from type hints + docstring. | Plain REST + hand-rolled function-calling glue per client — works, but loses cross-client portability, which is the whole point of using MCP. |
| **`httpx`** | Calls the Flask backend over HTTP from `backend_client.py`. Chosen because MCP tools are `async def` (so the server isn't blocked waiting on one backend request while another tool call could be handled), and `httpx` is the async-capable equivalent of `requests`. This is about talking to **our own backend** — unrelated to any AI/LLM provider. | `requests` — sync-only, would block the event loop on every backend call inside an async tool. |
| **`python-dotenv`** | Loads `BACKEND_API_URL` from `.env` so the backend URL is configurable per environment instead of hardcoded. | A full settings library (e.g. `pydantic-settings`) — overkill for one env var today. |
| **REST calls to the backend, not direct DB access** | The backend already owns validation, stock rules, and auth (`backend/CLAUDE.md`). Reimplementing any of that here would duplicate logic and risk drifting out of sync. | Importing backend models/SQLAlchemy directly — would tie this server to backend internals and duplicate business rules. |
| **Streamable HTTP transport (current)** | `ai-server` is a separate long-running process that connects to this server independently, not one spawned per-session by a single client (as stdio requires) — matches a real network service with potentially multiple/future clients. | stdio — fine for a single subprocess-per-client consumer (e.g. Claude Desktop alone), but doesn't fit a standalone service another process connects to over the network. |

### Not yet decided (will confront when we get there)

| Decision | The tradeoff | Current lean |
|---|---|---|
| **Auth passthrough** — how a customer's JWT reaches a tool that acts on their behalf (e.g. add-to-order) | With Streamable HTTP + a multi-user agent service, the token must arrive **per tool call** as an explicit argument (e.g. `auth_token: str`) — MCP has no Flask-style middleware to intercept it. MCP *does* define an OAuth-based auth flow for HTTP transport, but that's more machinery than needed until there's a concrete multi-user consumer. | Pass the token as a tool argument when we get there — matches the transport in use and what the existing gap note already implies. |
| **Cart / shopping-list model** | Backend feature (a real add-to-cart endpoint, new work in `backend/`) vs. agent-side conversation state (no backend change, but state lives only for that chat session). `POST /api/orders/` is one-shot checkout — must not be called per item. | Undecided — needs a decision before the next tool touches orders. |
| **LLM provider SDK for the future agent service** | Official provider SDK (`anthropic`, `openai`) is scoped to that one provider's API contract (endpoints, auth, request/response shape) — it cannot talk to a different provider, except where that provider deliberately mimics OpenAI's wire format (Ollama, vLLM, etc.). A unification library (e.g. LiteLLM) wraps many providers behind one call signature, at the cost of an extra abstraction layer. | Use the **`openai` SDK** directly (`ai-server/requirements.txt` already pins it) — no stated multi-provider requirement yet. Reach for LiteLLM only if/when multi-provider support becomes a real need — swapping later is a call-site change, not a rewrite. |

## Setup

```bash
cd mcp-server
python -m venv venv
.\venv\Scripts\Activate.ps1     # Windows PowerShell
pip install -r requirements.txt
copy .env.example .env          # defaults to http://localhost:3000
```

## Running

The backend must be running first (`python -m src.main` from `backend/`).
On Windows, the backend's startup log currently prints ✅/❌ emoji that
crash under the default console codepage (`UnicodeEncodeError` from
`cp1252`) — this is a pre-existing backend issue, not caused by this
server. Work around it for now with `$env:PYTHONIOENCODING="utf-8"` before
starting the backend, rather than editing backend startup logging.

This service is a standalone Streamable HTTP process — start it with
`python -m src.server` and leave it running, the same as the Flask
backend. Clients (`ai-server`, MCP Inspector) connect to it by URL;
nothing spawns it as a child process.

### Manual testing with MCP Inspector (do this before wiring up any agent)

With the server already running:

```bash
npx @modelcontextprotocol/inspector
```

Opens a browser UI — point it at `http://<MCP_HOST>:<MCP_PORT>/mcp`
(default `http://127.0.0.1:8000/mcp`) with transport "Streamable HTTP" to
call any of the tools above by hand and inspect the raw JSON response — no
LLM involved. Confirms the MCP layer works in isolation before adding
agent/LLM complexity on top.

### Connecting from Claude Desktop (optional, for interactive use)

Server must already be running. Add to Claude Desktop's
`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "supermarket": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

## Next steps (in order)

1. ~~Verify `get_products` end-to-end~~ — done: confirmed via a direct
   `call_tool()` smoke test that it reaches the live backend and returns
   real product data. Try it yourself via MCP Inspector too, for the
   interactive feel before an agent is in the loop.
2. ~~Add `get_product`, `get_category_tree`, `get_products_by_category`~~ —
   done: rounds out the read-only, no-auth product/category surface so a
   phase-1 chatbot can answer detail and browsing questions, not just search.
   Verify each via MCP Inspector before moving on.
3. Only then start the chatbot/agent service (a separate service that is an
   MCP *client* to this server, plus the Claude API for the conversation) —
   scoped to product Q&A only, no auth, no cart.
4. Decide the auth-passthrough pattern for tools that act on a specific user.
5. Decide the cart/shopping-list model (backend feature vs. agent-side state).
6. Add auth-protected tools (add-to-order, etc.) once both decisions above are made.
