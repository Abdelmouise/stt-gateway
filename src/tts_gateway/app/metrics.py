"""Lightweight Prometheus metrics + middleware.

We avoid third-party ``prometheus-fastapi-instrumentator`` because it has known
incompatibilities with recent FastAPI versions when sub-routers are used.
"""

from __future__ import annotations

import time

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUESTS = Counter(
    "tts_http_requests_total",
    "Total HTTP requests handled",
    ["method", "path", "status"],
)
LATENCY = Histogram(
    "tts_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
)
SYNTH_AUDIO_SECONDS = Histogram(
    "tts_synthesis_audio_seconds",
    "Duration of generated audio in seconds",
    ["lang", "backend"],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 60.0),
)
SYNTH_LATENCY = Histogram(
    "tts_synthesis_seconds",
    "Time to synthesize one request",
    ["lang", "backend"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0),
)


def _route_template(request: Request) -> str:
    """Return the route template (e.g. ``/v1/voices``) instead of the raw path.

    Falls back to the URL path if the route is not matched (e.g. 404).
    """
    route = request.scope.get("route")
    if route is not None and hasattr(route, "path"):
        return route.path
    return request.url.path


def install_metrics(app: FastAPI) -> None:
    @app.middleware("http")
    async def _prom_middleware(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        path = _route_template(request)
        # Don't pollute metrics with /metrics scrapes themselves.
        if path != "/metrics":
            REQUESTS.labels(request.method, path, str(response.status_code)).inc()
            LATENCY.labels(request.method, path).observe(elapsed)
        return response

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
