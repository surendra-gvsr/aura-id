# backend/app/middleware/subscription_gate.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.deps import get_supabase

BYPASS_PREFIXES = ("/health", "/api/v1/billing", "/api/v1/webhooks", "/docs", "/openapi")


class SubscriptionGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in BYPASS_PREFIXES):
            return await call_next(request)

        hotel_id = request.state.__dict__.get("hotel_id")
        if hotel_id is None:
            return await call_next(request)  # let auth middleware reject it

        db = get_supabase()
        result = (
            db.table("hotels")
            .select("subscription_status")
            .eq("id", hotel_id)
            .single()
            .execute()
        )

        if not result.data or result.data["subscription_status"] not in ("trialing", "active"):
            return JSONResponse(
                status_code=403,
                content={"success": False, "error": "Subscription inactive"},
            )

        return await call_next(request)
