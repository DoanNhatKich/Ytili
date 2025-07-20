"""Simple reverse proxy blueprint forwarding /api/v1/* requests from Flask to the FastAPI backend.

This allows the browser to keep using the same origin/port (5000) while
leveraging the existing FastAPI service on port 8000, without changing
frontend JavaScript code.
"""
from __future__ import annotations

import os
from flask import Blueprint, request, Response, current_app
import httpx

# URL of FastAPI backend, default to localhost:8000 but can be overridden via env
BACKEND_BASE = os.getenv("BACKEND_API_URL", "http://localhost:8000")
API_PREFIX = os.getenv("API_V1_STR", "/api/v1")  # should match FastAPI prefix

bp = Blueprint("api_proxy", __name__, url_prefix=API_PREFIX)


async def _forward_request(path: str):
    """Forward the incoming Flask request to FastAPI and stream back response."""

    # Construct full target URL
    target_url = f"{BACKEND_BASE}{API_PREFIX}/{path}"

    # Prepare request data
    method = request.method
    headers = {k: v for k, v in request.headers if k.lower() != "host"}
    params = request.args.to_dict(flat=False)  # include multi-value query params
    body = request.get_data()

    # Perform request asynchronously
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.request(method, target_url, params=params, content=body, headers=headers)

    # Build Flask response
    excluded_headers = {"content-encoding", "transfer-encoding", "content-length", "connection"}
    response_headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in excluded_headers]
    return Response(resp.content, resp.status_code, response_headers)


@bp.route("/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy(path: str):
    """Catch-all route under /api/v1 that forwards to FastAPI."""
    return await _forward_request(path)
