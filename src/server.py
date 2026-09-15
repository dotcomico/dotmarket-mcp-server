"""
MCP server exposing the Supermarket backend as MCP tools, for Claude
Desktop, MCP Inspector, and the ai-server chatbot/agent service.

Holds no business logic or DB access — every tool is a thin translation
to a Flask backend REST endpoint (see backend_client.py), keeping
validation, stock rules, and auth in one place per backend/CLAUDE.md.

Runs as a standalone Streamable HTTP service (own process, own port) so
any MCP client reaches it by URL — the same way this service itself
reaches the Flask backend — rather than being spawned as a child process.

Run standalone: python -m src.server
Inspect manually: npx @modelcontextprotocol/inspector
  (with the backend already running; point the inspector at
  http://<MCP_HOST>:<MCP_PORT>/mcp, transport "Streamable HTTP")
"""
import os

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from src import backend_client

load_dotenv()

mcp = FastMCP(
    "dotmarket",
    host=os.environ.get("MCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("MCP_PORT", "8000")),
)


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


@mcp.tool()
async def get_product(product_id: int) -> dict:
    """Look up a single product by its numeric id, with full detail.

    Use this after get_products has surfaced a product and the customer asks
    a follow-up like "tell me more about that one" or "what's the stock on
    product 12" — get_products' results already carry each product's id.

    Args:
        product_id: The numeric id of the product.

    Returns:
        {id, name, price, stock, description, category, ...} on success,
        or {"error": ...} if no product exists with that id.
    """
    try:
        return await backend_client.get_product(product_id)
    except httpx.HTTPStatusError as e:
        return {"error": f"Backend returned {e.response.status_code}: {e.response.text}"}
    except httpx.RequestError as e:
        return {"error": f"Could not reach backend API: {e}"}


@mcp.tool()
async def get_category_tree() -> list[dict] | dict:
    """Look up the full category tree (top-level categories with their
    subcategories nested inside).

    Use this to answer "what categories do you sell", "show me your
    sections", or to find a category's slug before calling
    get_products_by_category — categories are only two levels deep
    (top-level + subcategories), matching how the storefront browses them.

    Do NOT use this for price, stock, or "cheapest" questions — those
    have nothing to do with the category tree's shape. Use get_products
    or get_products_by_category for those instead.

    Returns:
        [{id, name, slug, children: [...]}, ...] — a list of top-level
        categories, each with its subcategories nested in "children".
    """
    try:
        return await backend_client.get_category_tree()
    except httpx.HTTPStatusError as e:
        return {"error": f"Backend returned {e.response.status_code}: {e.response.text}"}
    except httpx.RequestError as e:
        return {"error": f"Could not reach backend API: {e}"}


@mcp.tool()
async def get_products_by_category(
    slug: str,
    page: int = 1,
    limit: int = 20,
    min_price: float | None = None,
    max_price: float | None = None,
    search: str | None = None,
) -> dict:
    """Look up the products in a category (and its subcategories), by slug.

    Use this for browsing questions like "what's in your bakery category" or
    "show me dairy under $5", and for price/stock/"cheapest" questions scoped
    to a category — get the slug from get_category_tree first. Includes
    products in every subcategory under the given one. The results aren't
    pre-sorted by price — compare them yourself to answer "cheapest"/"most
    expensive" questions.

    Args:
        slug: The category's slug (from get_category_tree).
        page: 1-indexed page number for pagination.
        limit: Results per page (backend clamps to 100 max).
        min_price: Only products priced at or above this value.
        max_price: Only products priced at or below this value.
        search: Case-insensitive substring match on product name/description.

    Returns:
        {"products": [{id, name, price, stock, ...}, ...],
         "pagination": {total, page, limit, totalPages}}
        or {"error": ...} if no category exists with that slug.
    """
    try:
        return await backend_client.get_products_by_category(
            slug,
            page=page,
            limit=limit,
            min_price=min_price,
            max_price=max_price,
            search=search,
        )
    except httpx.HTTPStatusError as e:
        return {"error": f"Backend returned {e.response.status_code}: {e.response.text}"}
    except httpx.RequestError as e:
        return {"error": f"Could not reach backend API: {e}"}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
