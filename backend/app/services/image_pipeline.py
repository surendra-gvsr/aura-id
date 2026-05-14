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


import asyncio
from dataclasses import dataclass


@dataclass
class PipelineResult:
    image_bytes: bytes
    face_region_blacked_out: bool
    scan_id: str


def compress_image(image_bytes: bytes, max_longest_edge: int = 1600, quality: int = 85) -> bytes:
    """Resize so longest edge <= max_longest_edge, re-encode JPEG at given quality."""
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    longest = max(img.size)
    if longest > max_longest_edge:
        scale = max_longest_edge / longest
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=quality, optimize=True)
    return out.getvalue()


async def run_pipeline(image_bytes: bytes, content_type: str, scan_id: str) -> PipelineResult:
    """
    Run all pre-processing steps before Vertex AI.
    Steps: validate -> strip_exif -> face_blackout -> compress.
    Raises ValueError on validation failure.
    Raises RuntimeError if face blackout step fails unexpectedly.
    """
    validate_upload(image_bytes, content_type)

    clean_bytes = strip_exif(image_bytes)
    log.info("image_pipeline.exif_stripped", scan_id=scan_id)

    def _blackout_sync():
        img_arr = np.array(Image.open(io.BytesIO(clean_bytes)).convert("RGB"))
        img_bgr = cv2.cvtColor(img_arr, cv2.COLOR_RGB2BGR)
        return apply_face_blackout(img_bgr)

    try:
        loop = asyncio.get_running_loop()
        blacked_arr, face_found = await loop.run_in_executor(None, _blackout_sync)
    except Exception as exc:
        log.error("image_pipeline.face_blackout_failed", scan_id=scan_id, error=str(exc))
        raise RuntimeError(f"Face blackout step failed: {exc}") from exc

    log.info("image_pipeline.face_blacked_out", scan_id=scan_id, face_detected=face_found)

    blacked_rgb = cv2.cvtColor(blacked_arr, cv2.COLOR_BGR2RGB)
    pil_blacked = Image.fromarray(blacked_rgb)
    buf = io.BytesIO()
    pil_blacked.save(buf, format="JPEG", quality=95)
    compressed = compress_image(buf.getvalue())

    return PipelineResult(
        image_bytes=compressed,
        face_region_blacked_out=True,
        scan_id=scan_id,
    )
