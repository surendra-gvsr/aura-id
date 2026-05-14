# backend/app/services/retention.py
from datetime import datetime, timezone
import structlog
from supabase import Client
from apscheduler.schedulers.background import BackgroundScheduler

from app.deps import get_supabase

log = structlog.get_logger()


def delete_expired_images(db: Client | None = None) -> None:
    """Delete images from storage where retention period has elapsed."""
    if db is None:
        db = get_supabase()

    now_iso = datetime.now(timezone.utc).isoformat()

    result = (
        db.table("scans")
        .select("id, hotel_id, image_path")
        .not_("image_path", "is", None)
        .lte("image_deletion_scheduled_at", now_iso)
        .execute()
    )

    expired = result.data or []
    if not expired:
        return

    paths = [s["image_path"] for s in expired if s.get("image_path")]
    scan_ids = [s["id"] for s in expired]

    if paths:
        db.storage.from_("scan-images").remove(paths)

    db.table("scans").update({
        "image_path": None,
        "image_deleted_at": now_iso,
        "status": "expired",
    }).in_("id", scan_ids).execute()

    log.info("retention.images_deleted", count=len(scan_ids))


def start_retention_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(delete_expired_images, "interval", hours=1, id="retention_job")
    scheduler.start()
    log.info("retention.scheduler_started", interval_hours=1)
    return scheduler
