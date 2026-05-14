# agent/src/pii_guard.py
"""
Memory-scrubbing helpers.

PII string fields are replaced with empty strings before the object is
released. Python's GC does not guarantee OS-level memory zeroing, but
removing values from the live object graph is the practical compliance
boundary for a desktop agent that does not swap guest data to disk.
"""

import gc

from src.models import ScanData

PII_FIELD_NAMES = frozenset(
    {
        "last_name",
        "first_name",
        "dob",
        "doc_number",
        "address_line_1",
        "address_line_2",
        "city",
        "postal_code",
        "email",
    }
)


def wipe(scan: ScanData | None) -> None:
    """Zero all PII string fields on scan, then trigger GC."""
    if scan is None:
        return
    for field_name in PII_FIELD_NAMES:
        value = getattr(scan, field_name, None)
        if isinstance(value, str):
            setattr(scan, field_name, "")
    gc.collect()


def wipe_dict(d: dict) -> None:
    """Zero all PII keys in a raw dict (used for unexpected response shapes)."""
    for key in PII_FIELD_NAMES:
        if key in d and isinstance(d[key], str):
            d[key] = ""
    gc.collect()
