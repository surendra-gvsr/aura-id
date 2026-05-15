import structlog
from supabase import Client

log = structlog.get_logger()


async def write_audit_log(
    *,
    db: Client,
    hotel_id: str | None = None,
    user_id: str | None = None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Append-only audit log write. Never raises — failure is logged but swallowed."""
    try:
        db.table("audit_log").insert({
            "hotel_id": hotel_id,
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "metadata": metadata or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
        }).execute()
    except Exception as exc:
        # Log failure but never propagate — audit must not break the request path
        log.error("audit_log.write_failed", action=action, error=str(exc))
