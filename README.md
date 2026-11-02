# 🛒 Dotmarket MCP Server

Lets AI models use **[Dotmarket](https://github.com/dotcomico/dotmarket)** store data. It exposes the backend API as a set of tools that any [MCP](https://modelcontextprotocol.io) client can call.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![MCP](https://img.shields.io/badge/MCP-Streamable%20HTTP-6E56CF)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> [!NOTE]
> This is one of four repos that make up Dotmarket. For the overview, screenshots and full setup, start with the **[main repo](https://github.com/dotcomico/dotmarket)**.

**What is MCP?** The Model Context Protocol is a standard way for AI applications to discover and call tools. Without it, each AI client would need its own custom integration with the backend. With it, one server works with any MCP client.

## 🧰 Tools

Every tool is read-only and needs no login.

| Tool | What it does | Backend endpoint |
|---|---|---|
| `get_products` | Searches products by name, category or price | `GET /api/products/` |
| `get_product` | Gets full details for one product | `GET /api/products/<id>` |
| `get_category_tree` | Lists all categories and their subcategories | `GET /api/categories/tree` |
| `get_products_by_category` | Lists products in a category and its subcategories | `GET /api/categories/<slug>/products` |

## 🏗️ How It Works

```
MCP client (ai-server, or MCP Inspector for manual testing)
        │  MCP protocol over Streamable HTTP
        ▼
  src/server.py          Tool definitions. The AI model reads each tool's
        │                description to decide when to call it.
        ▼
  src/backend_client.py  Thin HTTP wrapper. The only file that knows the
        │                backend's address and endpoints.
        ▼  HTTP
  Dotmarket backend      Owns all data, validation and business rules.
```

Each tool only translates: tool call → HTTP request → backend response → tool result.

**Why not read the database directly?** The backend already owns validation, stock rules and auth. Repeating them here would duplicate logic, and the two copies could drift apart.

If the backend returns an error or can't be reached, a tool returns `{"error": "..."}` instead of crashing, so the client still gets a usable result.

## 🚀 Getting Started

**You need:**
- Python 3.11+
- The [Dotmarket backend](https://github.com/dotcomico/dotmarket-server) running at `http://localhost:3000`

```bash
git clone https://github.com/dotcomico/dotmarket-mcp-server.git mcp-server
cd mcp-server

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env            # Windows: copy .env.example .env
python -m src.server
```

The server listens at `http://127.0.0.1:8000/mcp`. Leave it running, because clients connect to it by URL.

### Environment variables

| Variable | Description | Default |
|---|---|---|
| `BACKEND_API_URL` | Address of the Dotmarket backend | `http://localhost:3000` |
| `MCP_HOST` | Address this server listens on | `127.0.0.1` |
| `MCP_PORT` | Port this server listens on | `8000` |

## 🧪 Trying It Out

You can call the tools by hand, with no AI model involved, using the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector
```

In the browser window that opens:

1. Set the transport to **Streamable HTTP**.
2. Set the URL to `http://127.0.0.1:8000/mcp`.
3. Connect, open **Tools**, and run `get_category_tree`.

You should see the store's categories as JSON.

To connect from Claude Code instead:

```bash
claude mcp add --transport http dotmarket http://127.0.0.1:8000/mcp
```

## 🚧 Known Limitations

- **No customer-specific tools yet.** A tool that acts for one customer, such as adding to their order, needs their login forwarded to the backend. That pattern hasn't been built.
- **No shopping-cart tool yet.** `POST /api/orders/` is a one-shot checkout that creates a real order and reduces stock, so a tool must not call it once per item. The cart design has to be decided first.

<details>
<summary><b>Technical decisions</b></summary>

### Decided

| Choice | Why | Alternative not chosen |
|---|---|---|
| **MCP (`mcp` / `FastMCP`)** | Any MCP client can call the backend as typed tools. `@mcp.tool()` builds each schema from type hints and the docstring. | Plain REST with custom glue per client, which loses portability between clients. |
| **`httpx`** | Tools are `async def`, and `httpx` lets one backend call wait without blocking other tool calls. | `requests`, which is sync-only and would block the event loop. |
| **`python-dotenv`** | Keeps the backend address configurable per environment. | A full settings library, which is more than a few env vars need. |
| **REST calls, not database access** | The backend stays the single owner of its rules. | Importing backend models, which would tie this server to backend internals. |
| **Streamable HTTP transport** | `ai-server` is a separate long-running process that connects over the network. | stdio, which suits one client spawning its own subprocess. |

### Not decided yet

| Decision | Tradeoff | Current lean |
|---|---|---|
| **Forwarding a customer's login** | With Streamable HTTP and many users, the token must arrive with each tool call. MCP also defines an OAuth flow, but that's more than is needed before there's a real multi-user tool. | Pass the token as a tool argument. |
| **Cart model** | A real backend cart endpoint means new backend work. Keeping the cart in the chat session needs no backend change, but it only lasts for that chat. | Undecided. |

</details>

## 🔗 Related Repos

| Repo | Role |
|---|---|
| [`dotmarket`](https://github.com/dotcomico/dotmarket) | Overview, docs and Docker Compose |
| [`dotmarket-client`](https://github.com/dotcomico/dotmarket-client) | Storefront and admin UI |
| [`dotmarket-server`](https://github.com/dotcomico/dotmarket-server) | REST API, auth and database |
| [`dotmarket-ai-server`](https://github.com/dotcomico/dotmarket-ai-server) | Chat assistant that uses these tools |

## 📄 License

[MIT](LICENSE)
