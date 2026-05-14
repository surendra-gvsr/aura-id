from datetime import date
from typing import Literal
from pydantic import BaseModel, Field


class ParsedID(BaseModel):
    """Vertex AI structured output schema. Text fields only — no biometric data."""
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    dob: date | None = None
    doc_type: Literal["passport", "drivers_license", "national_id", "other"] | None = None
    doc_number: str | None = None
    doc_country: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    nationality: str | None = None
    sex: Literal["M", "F", "X"] | None = None
    expiry_date: date | None = None
    mrz_line_1: str | None = None
    mrz_line_2: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ScanResponse(BaseModel):
    id: str
    status: str
    parsed_data: ParsedID | None = None
    face_region_blacked_out: bool
    created_at: str
    parsed_at: str | None = None
    typed_at: str | None = None
    error_message: str | None = None
