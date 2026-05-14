# backend/app/services/image_pipeline.py
import io
import piexif
import numpy as np
import cv2
import mediapipe as mp
import structlog
from PIL import Image

log = structlog.get_logger()

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


def apply_face_blackout(img: np.ndarray) -> tuple[np.ndarray, bool]:
    """
    Detect all faces and paint solid black over each bounding box (+ 10% padding).
    Returns (modified_image, face_was_detected).
    This is the BIPA-critical step. Must run on every image before Vertex AI.
    """
    h, w = img.shape[:2]
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    result_img = img.copy()
    face_found = False

    detector = mp.solutions.face_detection.FaceDetection(
        model_selection=0, min_detection_confidence=0.5
    )
    results = detector.process(rgb)

    if not results.detections:
        log.info("image_pipeline.no_face_detected")
        return result_img, False

    for detection in results.detections:
        face_found = True
        bbox = detection.location_data.relative_bounding_box
        pad_x = bbox.width * 0.10
        pad_y = bbox.height * 0.10
        x1 = max(0, int((bbox.xmin - pad_x) * w))
        y1 = max(0, int((bbox.ymin - pad_y) * h))
        x2 = min(w, int((bbox.xmin + bbox.width + pad_x) * w))
        y2 = min(h, int((bbox.ymin + bbox.height + pad_y) * h))
        result_img[y1:y2, x1:x2] = 0

    log.info("image_pipeline.face_blacked_out", face_count=len(results.detections))
    return result_img, face_found
