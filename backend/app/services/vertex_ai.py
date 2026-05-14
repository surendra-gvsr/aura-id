# backend/app/services/vertex_ai.py
from abc import ABC, abstractmethod
from app.models.scan import ParsedID


class AbstractVertexClient(ABC):
    @abstractmethod
    async def extract_id_fields(self, image_bytes: bytes) -> ParsedID:
        """Extract text fields from an ID image. Never returns biometric data."""
        ...


class FakeVertexClient(AbstractVertexClient):
    """In-memory stub for tests. No network calls."""

    def __init__(self, response: ParsedID | None = None, raise_error: Exception | None = None):
        self._response = response or ParsedID(confidence=0.9)
        self._raise_error = raise_error

    async def extract_id_fields(self, image_bytes: bytes) -> ParsedID:
        if self._raise_error:
            raise self._raise_error
        return self._response


import re
import json
import asyncio
import structlog
import vertexai
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig

from app.config import settings

log = structlog.get_logger()

_BIOMETRIC_PATTERNS = re.compile(
    r"\b(eye[s]?|iris|pupil|retina|complexion|skin tone|hair color|"
    r"blonde|brunette|bald|nose|mouth|lips|ears|jaw|chin|cheek|"
    r"facial feature|portrait|photograph of|image of the person)\b",
    re.IGNORECASE,
)

_EXTRACTION_PROMPT = (
    "You are a document OCR system. Extract ONLY the text fields from the "
    "government-issued ID shown. Return a JSON object matching the schema. "
    "Do NOT describe, analyze, or comment on the photograph, face, or physical "
    "appearance of any person in the image. Extract text only."
)

_VERTEX_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "first_name": {"type": "STRING"},
        "last_name": {"type": "STRING"},
        "middle_name": {"type": "STRING"},
        "dob": {"type": "STRING"},
        "doc_type": {"type": "STRING", "enum": ["passport", "drivers_license", "national_id", "other"]},
        "doc_number": {"type": "STRING"},
        "doc_country": {"type": "STRING"},
        "address_line_1": {"type": "STRING"},
        "address_line_2": {"type": "STRING"},
        "city": {"type": "STRING"},
        "state": {"type": "STRING"},
        "postal_code": {"type": "STRING"},
        "nationality": {"type": "STRING"},
        "sex": {"type": "STRING", "enum": ["M", "F", "X"]},
        "expiry_date": {"type": "STRING"},
        "mrz_line_1": {"type": "STRING"},
        "mrz_line_2": {"type": "STRING"},
        "confidence": {"type": "NUMBER"},
    },
}


def check_for_biometric_content(text: str) -> bool:
    """Returns True if response text appears to contain biometric descriptions."""
    return bool(_BIOMETRIC_PATTERNS.search(text))


class VertexAIClient(AbstractVertexClient):
    def __init__(self) -> None:
        vertexai.init(project=settings.gcp_project_id, location=settings.vertex_location)
        self._model = GenerativeModel("gemini-2.5-flash")

    async def extract_id_fields(self, image_bytes: bytes) -> ParsedID:
        def _call() -> ParsedID:
            image_part = Part.from_data(data=image_bytes, mime_type="image/jpeg")
            response = self._model.generate_content(
                contents=[image_part, _EXTRACTION_PROMPT],
                generation_config=GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=_VERTEX_SCHEMA,
                    temperature=0,
                ),
            )
            raw_text = response.text

            if check_for_biometric_content(raw_text):
                log.error("vertex_ai.biometric_content_detected", preview=raw_text[:100])
                raise ValueError("Vertex AI response contained biometric content — rejected")

            data = json.loads(raw_text)
            return ParsedID.model_validate(data)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _call)
