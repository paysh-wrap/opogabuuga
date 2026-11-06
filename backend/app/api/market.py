"""Market panel (OpenBB, display only)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.deps import Principal, current_user

router = APIRouter(prefix="/api")


@router.get("/market/openbb")
async def openbb(request: Request, _: Principal = Depends(current_user)) -> dict[str, Any]:
    st = request.app.state
    if not hasattr(st, "openbb"):
        from app.market.openbb_feed import OpenBBFeed

        st.openbb = OpenBBFeed()
    snap: dict[str, Any] = st.openbb.snapshot()
    return snap
