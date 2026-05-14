import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


def make_creds(token: str) -> HTTPAuthorizationCredentials:
    c = MagicMock(spec=HTTPAuthorizationCredentials)
    c.credentials = token
    return c


@pytest.mark.asyncio
async def test_get_current_user_rejects_invalid_token():
    from app.deps import get_current_user
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=make_creds("not-a-jwt"))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_workstation_rejects_wrong_prefix():
    from app.deps import get_current_workstation
    request = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await get_current_workstation(request=request, credentials=make_creds("Bearer wrong"))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_workstation_rejects_revoked(monkeypatch):
    from app.deps import get_current_workstation
    import bcrypt as _bcrypt

    token = "ws_test_" + "a" * 32
    raw_hash = _bcrypt.hashpw(token.encode(), _bcrypt.gensalt()).decode()

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "ws-1", "hotel_id": "h-1", "token_hash": raw_hash, "revoked_at": "2024-01-01T00:00:00Z"}]
    )
    monkeypatch.setattr("app.deps.get_supabase", lambda: mock_db)

    request = MagicMock()
    with pytest.raises(HTTPException) as exc:
        await get_current_workstation(request=request, credentials=make_creds(token))
    assert exc.value.status_code == 401
    assert "revoked" in exc.value.detail.lower()
