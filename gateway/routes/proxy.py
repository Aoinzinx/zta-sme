# gateway/routes/proxy.py — Upstream Request Proxying

import os
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
import httpx

router = APIRouter()

UPSTREAM_AWS   = os.environ["UPSTREAM_AWS_URL"]    # Lambda API Gateway endpoint
UPSTREAM_AZURE = os.environ["UPSTREAM_AZURE_URL"]  # Azure App Service endpoint

ROUTE_TABLE = {
    "/aws/":   UPSTREAM_AWS,
    "/azure/": UPSTREAM_AZURE,
}


def resolve_upstream(path: str) -> str:
    """Map an incoming path prefix to the appropriate upstream base URL."""
    for prefix, upstream in ROUTE_TABLE.items():
        if path.startswith(prefix):
            # Strip the leading prefix and append remainder to upstream
            return upstream + path[len(prefix) - 1:]
    raise ValueError(f"No upstream configured for path: {path}")


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
)
async def proxy_request(request: Request, path: str):
    """
    Forward all permitted requests to the appropriate upstream cloud resource.
    By the time this handler runs, the middleware has already:
      - validated the JWT,
      - checked the revocation list, and
      - received a 'permit' decision from the Policy Engine.
    """
    try:
        upstream_url = resolve_upstream(request.url.path)
    except ValueError:
        return JSONResponse(status_code=404, content={"detail": "Resource not found"})

    body = await request.body()

    # Strip hop-by-hop headers before forwarding
    hop_by_hop = {"host", "content-length", "transfer-encoding", "connection"}
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in hop_by_hop
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            upstream_resp = await client.request(
                method=request.method,
                url=upstream_url,
                headers=headers,
                content=body,
            )
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        return JSONResponse(
            status_code=502,
            content={"detail": f"Upstream service unreachable: {type(exc).__name__}"}
        )

    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=dict(upstream_resp.headers),
        media_type=upstream_resp.headers.get("content-type"),
    )
