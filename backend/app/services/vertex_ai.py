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
