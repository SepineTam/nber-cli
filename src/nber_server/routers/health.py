from __future__ import annotations

from importlib.metadata import version as get_version
from pathlib import Path

from fastapi import APIRouter, Request

from nber_server.errors import api_success
from nber_server.schemas import HealthResponse

router = APIRouter(prefix="/api/v1", tags=["health"])


def _package_version() -> str:
    try:
        return get_version("nber-cli")
    except Exception:
        return "0.11.0"


@router.get("/health")
async def health(request: Request):
    data = HealthResponse(
        status="ok",
        version=_package_version(),
        db_path=str(Path(request.app.state.db_path)),
    )
    return api_success(data.model_dump())
