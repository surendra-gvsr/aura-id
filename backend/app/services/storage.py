# backend/app/services/storage.py
import structlog
from supabase import Client

BUCKET = "scan-images"
log = structlog.get_logger()


def upload_scan_image(*, db: Client, hotel_id: str, scan_id: str, image_bytes: bytes) -> str:
    """Upload a processed scan image to Supabase Storage. Returns the storage path."""
    path = f"scans/{hotel_id}/{scan_id}.jpg"
    db.storage.from_(BUCKET).upload(
        path=path,
        file=image_bytes,
        file_options={"content-type": "image/jpeg", "upsert": "true"},
    )
    log.info("storage.uploaded", scan_id=scan_id, path=path)
    return path


def get_signed_url(*, db: Client, path: str, expires_in: int = 300) -> str:
    """Generate a short-lived signed URL for secure, time-limited image access."""
    result = db.storage.from_(BUCKET).create_signed_url(path, expires_in)
    return result["signedURL"]


def delete_scan_image(*, db: Client, path: str) -> None:
    """Permanently remove a scan image from storage (used by retention job)."""
    db.storage.from_(BUCKET).remove([path])
    log.info("storage.deleted", path=path)
