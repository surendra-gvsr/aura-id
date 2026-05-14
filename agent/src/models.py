# agent/src/models.py
from dataclasses import dataclass


@dataclass
class ScanData:
    """
    In-memory only. Never written to disk or logged.
    Call pii_guard.wipe() immediately after use.
    """

    scan_id: str
    pms_profile_name: str
    last_name: str | None = None
    first_name: str | None = None
    dob: str | None = None
    doc_number: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    postal_code: str | None = None
    email: str | None = None
