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
