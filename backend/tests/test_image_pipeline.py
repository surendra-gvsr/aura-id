# backend/tests/test_image_pipeline.py
import io
import pytest
import piexif
from PIL import Image
from app.services.image_pipeline import validate_upload, strip_exif

ALLOWED_TYPES = {"image/jpeg", "image/png"}


def make_jpeg_with_exif() -> bytes:
    """Create a minimal JPEG with GPS EXIF data."""
    img = Image.new("RGB", (100, 100), color=(128, 128, 128))
    exif_dict = {
        "GPS": {
            piexif.GPSIFD.GPSLatitude: ((40, 1), (26, 1), (4600, 100)),
            piexif.GPSIFD.GPSLongitude: ((79, 1), (58, 1), (3400, 100)),
        }
    }
    exif_bytes = piexif.dump(exif_dict)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif_bytes)
    return buf.getvalue()


def make_plain_jpeg() -> bytes:
    img = Image.new("RGB", (100, 100), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_validate_upload_accepts_jpeg():
    data = make_plain_jpeg()
    validate_upload(data, "image/jpeg")  # should not raise


def test_validate_upload_rejects_oversized():
    data = b"x" * (9 * 1024 * 1024)  # 9MB
    with pytest.raises(ValueError, match="exceeds"):
        validate_upload(data, "image/jpeg")


def test_validate_upload_rejects_mime_mismatch():
    data = make_plain_jpeg()  # JPEG bytes
    with pytest.raises(ValueError, match="MIME"):
        validate_upload(data, "image/png")  # wrong MIME


def test_strip_exif_removes_gps():
    original = make_jpeg_with_exif()
    stripped = strip_exif(original)
    img = Image.open(io.BytesIO(stripped))
    exif_data = img.info.get("exif", b"")
    if exif_data:
        exif_dict = piexif.load(exif_data)
        assert not exif_dict.get("GPS"), "GPS data must be removed"


def test_strip_exif_output_is_valid_jpeg():
    original = make_jpeg_with_exif()
    stripped = strip_exif(original)
    img = Image.open(io.BytesIO(stripped))
    assert img.format == "JPEG"
