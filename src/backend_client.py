"""
Thin HTTP client for the Flask backend. The only place that knows the
backend's base URL and endpoint shapes — server.py must go through this
module rather than calling httpx directly.

No caching, retries, or auth handling. Auth passthrough for tools acting
on a customer's behalf (e.g. a future add-to-order tool) is unhandled —
see README.md.
"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://localhost:3000")


async def get_products(
    search: str | None = None,
    category_id: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    page: int = 1,
    limit: int = 10,
) -> dict:
    """Calls GET /api/products/ on the backend. Raises httpx.HTTPStatusError
    on a non-2xx response — callers decide how to surface that."""
    params = {"page": page, "limit": limit}
    if search:
        params["search"] = search
    if category_id is not None:
        params["categoryId"] = category_id
    if min_price is not None:
        params["minPrice"] = min_price
    if max_price is not None:
        params["maxPrice"] = max_price

    async with httpx.AsyncClient(base_url=BACKEND_API_URL, timeout=10.0) as client:
        response = await client.get("/api/products/", params=params)
        response.raise_for_status()
        return response.json()


async def get_product(product_id: int) -> dict:
    """Calls GET /api/products/<id> on the backend. Raises
    httpx.HTTPStatusError (404 if the id doesn't exist) — callers decide how
    to surface that."""
    async with httpx.AsyncClient(base_url=BACKEND_API_URL, timeout=10.0) as client:
        response = await client.get(f"/api/products/{product_id}")
        response.raise_for_status()
        return response.json()


def _slim_category(node: dict) -> dict:
    """Strips a backend category node down to what the LLM tool actually
    uses (id, name, slug, children) — the raw node also carries parentId,
    icon, image, and timestamps meant for the storefront/admin UI, not a
    chat tool result."""
    return {
        "id": node["id"],
        "name": node["name"],
        "slug": node["slug"],
        "children": [_slim_category(child) for child in node.get("children", [])],
    }


async def get_category_tree() -> list:
    """Calls GET /api/categories/tree on the backend. Raises
    httpx.HTTPStatusError on a non-2xx response — callers decide how to
    surface that."""
    async with httpx.AsyncClient(base_url=BACKEND_API_URL, timeout=10.0) as client:
        response = await client.get("/api/categories/tree")
        response.raise_for_status()
        return [_slim_category(node) for node in response.json()]


async def get_products_by_category(
    slug: str,
    page: int = 1,
    limit: int = 20,
    min_price: float | None = None,
    max_price: float | None = None,
    search: str | None = None,
) -> dict:
    """Calls GET /api/categories/<slug>/products on the backend. Raises
    httpx.HTTPStatusError (404 if the slug doesn't exist) — callers decide
    how to surface that."""
    params = {"page": page, "limit": limit}
    if min_price is not None:
        params["minPrice"] = min_price
    if max_price is not None:
        params["maxPrice"] = max_price
    if search:
        params["search"] = search

    async with httpx.AsyncClient(base_url=BACKEND_API_URL, timeout=10.0) as client:
        response = await client.get(f"/api/categories/{slug}/products", params=params)
        response.raise_for_status()
        return response.json()
