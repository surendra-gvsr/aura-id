import re

_DOB_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
# Only scrub explicit doc_number= key=value pairs in log strings, not freeform text
_DOC_NUM_EXPLICIT_RE = re.compile(r'(doc_number["\s:=]+)[A-Z0-9]{5,}', re.IGNORECASE)


def mask_name(first: str | None, last: str | None) -> str:
    """Return 'J. Smith' format. Returns initial-only if no last name."""
    if first and not last:
        return f"{first[0]}."
    if not last:
        return ""
    initial = f"{first[0]}. " if first else ""
    return f"{initial}{last}"


def mask_doc_number(doc_number: str | None) -> str | None:
    if not doc_number:
        return None
    return f"****{doc_number[-4:]}" if len(doc_number) >= 4 else "****"


def scrub_pii_from_string(text: str) -> str:
    """Best-effort PII scrub for log strings. Not a security boundary.
    Primary protection is key-based removal in _pii_scrub_processor."""
    text = _DOB_RE.sub("[DOB_REDACTED]", text)
    text = _DOC_NUM_EXPLICIT_RE.sub(r"\1****", text)
    return text
