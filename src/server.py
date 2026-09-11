"""
MCP server exposing the Supermarket backend as MCP tools, for Claude
Desktop, MCP Inspector, and future chatbot agents.

Holds no business logic or DB access — every tool is a thin translation
to a Flask backend REST endpoint (see backend_client.py), keeping
validation, stock rules, and auth in one place per backend/CLAUDE.md.

Run standalone: npx @modelcontextprotocol/inspector python -m src.server
(from mcp-server/, with the backend already running)
"""
import httpx
from mcp.server.fastmcp import FastMCP

from src import backend_client

mcp = FastMCP("supermarket")


@mcp.tool()
async def get_products(
    search: str | None = None,
    category_id: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    page: int = 1,
    limit: int = 10,
) -> dict:
    """Look up supermarket products, including name, price, and stock.

    Use this to answer customer questions like "what products do you have",
    "how much does X cost", or "do you have anything under $5". Supports
    a case-insensitive name search, category/price filtering, and pagination
    (max 100 results per page — the backend clamps this).

    Args:
        search: Case-insensitive substring match on product name.
        category_id: Filter to a single category by its numeric id.
        min_price: Only products priced at or above this value.
        max_price: Only products priced at or below this value.
        page: 1-indexed page number for pagination.
        limit: Results per page (backend clamps to 100 max).

    Returns:
        {"products": [{id, name, price, stock, category, ...}, ...],
         "pagination": {total, page, limit, totalPages}}
    """
    try:
        return await backend_client.get_products(
            search=search,
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            page=page,
            limit=limit,
        )
    except httpx.HTTPStatusError as e:
        return {"error": f"Backend returned {e.response.status_code}: {e.response.text}"}
    except httpx.RequestError as e:
        return {"error": f"Could not reach backend API: {e}"}


if __name__ == "__main__":
    mcp.run()
