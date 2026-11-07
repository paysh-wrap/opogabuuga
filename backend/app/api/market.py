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
    try:  # optional OpenBB keys saved on the Connections page (decrypted only here, never returned)
        from app.connections.service import credentials
        from app.crypto import Vault

        with st.sessionmaker() as s:
            st.openbb.creds = credentials(s, Vault(st.settings.master_key.get_secret_value()), "openbb") or {}
    except Exception:  # keys are optional; the free feed works without them
        st.openbb.creds = {}
    snap: dict[str, Any] = st.openbb.snapshot()
    return snap
