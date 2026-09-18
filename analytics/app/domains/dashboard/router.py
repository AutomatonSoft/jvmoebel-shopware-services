from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from domains.base.dependencies import require_dashboard_access
from domains.dashboard.shops import DashboardConfig, dashboard_config

DIST_DIR = Path(__file__).resolve().parents[3] / "dashboard" / "dist"

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(require_dashboard_access)],
    include_in_schema=False,
)


def _safe_dist_file(relative: str) -> Path | None:
    if not DIST_DIR.exists():
        return None
    root = DIST_DIR.resolve()
    target = (DIST_DIR / relative).resolve()
    if not str(target).startswith(str(root)):
        return None
    if target.is_file():
        return target
    return None


@router.get("/config", response_model=DashboardConfig)
async def get_dashboard_config() -> DashboardConfig:
    return dashboard_config()


@router.get("")
@router.get("/")
@router.get("/{full_path:path}")
async def dashboard_spa(full_path: str = "") -> FileResponse:
    existing = _safe_dist_file(full_path)
    if existing is not None:
        return FileResponse(existing)
    index = _safe_dist_file("index.html")
    if index is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dashboard UI is not built",
        )
    return FileResponse(index)
