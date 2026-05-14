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


import numpy as np
import cv2
from unittest.mock import patch, MagicMock
from app.services.image_pipeline import apply_face_blackout


def make_white_numpy_image(h=200, w=300) -> np.ndarray:
    return np.ones((h, w, 3), dtype=np.uint8) * 255


def test_face_blackout_zeroes_detected_region():
    """Core compliance test: face region pixels must be (0,0,0) after blackout."""
    img = make_white_numpy_image()

    fake_detection = MagicMock()
    fake_bbox = MagicMock()
    fake_bbox.xmin = 100 / 300
    fake_bbox.ymin = 50 / 200
    fake_bbox.width = 80 / 300
    fake_bbox.height = 100 / 200
    fake_detection.location_data.relative_bounding_box = fake_bbox

    mock_results = MagicMock()
    mock_results.detections = [fake_detection]

    with patch("app.services.image_pipeline.mp") as mock_mp:
        detector_instance = MagicMock()
        detector_instance.process.return_value = mock_results
        mock_mp.solutions.face_detection.FaceDetection.return_value = detector_instance

        result, face_found = apply_face_blackout(img)

    assert face_found is True
    cx, cy = 140, 100  # center of detected face
    assert np.all(result[cy - 5 : cy + 5, cx - 5 : cx + 5] == 0), \
        "Center of face region must be all black pixels"


def test_face_blackout_no_face_returns_original():
    img = make_white_numpy_image()
    mock_results = MagicMock()
    mock_results.detections = None

    with patch("app.services.image_pipeline.mp") as mock_mp:
        detector_instance = MagicMock()
        detector_instance.process.return_value = mock_results
        mock_mp.solutions.face_detection.FaceDetection.return_value = detector_instance

        result, face_found = apply_face_blackout(img)

    assert face_found is False
    assert np.all(result == 255)  # original white image unchanged


def test_face_blackout_does_not_modify_outside_bbox():
    img = make_white_numpy_image(200, 300)
    fake_detection = MagicMock()
    fake_bbox = MagicMock()
    fake_bbox.xmin = 0.3
    fake_bbox.ymin = 0.3
    fake_bbox.width = 0.2
    fake_bbox.height = 0.2
    fake_detection.location_data.relative_bounding_box = fake_bbox
    mock_results = MagicMock()
    mock_results.detections = [fake_detection]

    with patch("app.services.image_pipeline.mp") as mock_mp:
        detector_instance = MagicMock()
        detector_instance.process.return_value = mock_results
        mock_mp.solutions.face_detection.FaceDetection.return_value = detector_instance

        result, _ = apply_face_blackout(img)

    assert np.all(result[0:10, 0:10] == 255)
