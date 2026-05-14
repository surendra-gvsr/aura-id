import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter
from slowapi.util import get_remote_address
from supabase import create_client, Client

from app.config import settings

security = HTTPBearer()


def get_supabase() -> Client:
    # Creates a Supabase client using service-role key from env — never hardcoded
    return create_client(settings.supabase_url, settings.supabase_service_key)


def _workstation_or_ip_key(request: Request) -> str:
    # Use the workstation token prefix as rate-limit key if present, else fall back to IP
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ws_"):
        return f"ws:{auth[7:19]}"
    return get_remote_address(request)


# General IP-based limiter for clerk/user routes
limiter = Limiter(key_func=get_remote_address)

# Workstation-aware limiter keyed by token prefix or IP
workstation_limiter = Limiter(key_func=_workstation_or_ip_key)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Validates a Supabase-issued JWT and extracts user identity."""
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_exp": True},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # hotel_id may be in root payload or nested in app_metadata
    hotel_id = (
        payload.get("hotel_id")
        or payload.get("app_metadata", {}).get("hotel_id")
    )
    if not hotel_id:
        raise HTTPException(status_code=401, detail="Missing hotel_id claim")

    return {
        "user_id": payload["sub"],
        "hotel_id": hotel_id,
        "role": payload.get("role", "clerk"),
    }


async def get_current_workstation(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Validates a workstation bearer token (ws_live_ or ws_test_ prefix) against DB hash."""
    token = credentials.credentials

    # Only accept tokens with the expected format prefix
    if not (token.startswith("ws_live_") or token.startswith("ws_test_")):
        raise HTTPException(status_code=401, detail="Invalid workstation token format")

    db = get_supabase()
    # Lookup by the first 12 chars as a non-secret prefix index — full token is bcrypt-verified
    prefix = token[:12]
    result = (
        db.table("workstations")
        .select("id, hotel_id, token_hash, revoked_at")
        .eq("token_prefix", prefix)
        .execute()
    )

    workstation = None
    for row in result.data or []:
        # bcrypt constant-time comparison — protects against timing attacks
        if row.get("token_hash") and bcrypt.checkpw(token.encode(), row["token_hash"].encode()):
            workstation = row
            break

    if not workstation:
        raise HTTPException(status_code=401, detail="Workstation not found")
    if workstation.get("revoked_at"):
        raise HTTPException(status_code=401, detail="Workstation token revoked")

    return {
        "workstation_id": workstation["id"],
        "hotel_id": workstation["hotel_id"],
    }
