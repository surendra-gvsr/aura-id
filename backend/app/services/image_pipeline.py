# backend/app/services/image_pipeline.py
import io
import piexif
from PIL import Image

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8MB

_MAGIC_BYTES = {
    "image/jpeg": [(0, b"\xff\xd8\xff")],
    "image/png": [(0, b"\x89PNG")],
    "image/heic": [(4, b"ftyp")],
}


def validate_upload(data: bytes, content_type: str) -> None:
    """Raises ValueError if data is too large or MIME doesn't match bytes."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Upload exceeds {MAX_UPLOAD_BYTES // (1024*1024)}MB limit")

    ct = content_type.split(";")[0].strip().lower()
    if ct not in _MAGIC_BYTES:
        raise ValueError(f"Unsupported content type: {ct}")

    for offset, magic in _MAGIC_BYTES[ct]:
        if data[offset : offset + len(magic)] != magic:
            raise ValueError(f"MIME type {ct} does not match file bytes")


def strip_exif(image_bytes: bytes) -> bytes:
    """Strip all EXIF/metadata and re-encode through Pillow as JPEG."""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    out = io.BytesIO()
    img.save(out, format="JPEG", exif=piexif.dump({}), quality=95)
    return out.getvalue()
