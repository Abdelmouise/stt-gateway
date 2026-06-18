"""Health & readiness endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from tts_gateway.app.backends import BackendBase
from tts_gateway.app.deps import get_backend_dep

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz(
    request: Request,
    backend: Annotated[BackendBase, Depends(get_backend_dep)],
) -> dict[str, object]:
    if not getattr(backend, "_loaded", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Backend not loaded",
        )
    return {
        "status": "ready",
        "backend": backend.name,
        "device": backend.device,
        "supported_langs": sorted(backend.supported_langs),
    }
