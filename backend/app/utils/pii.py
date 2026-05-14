import re

_DOB_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_DOC_NUM_RE = re.compile(r"\b([A-Z0-9]{2,4})\d{4,}\b")


def mask_name(first: str | None, last: str | None) -> str:
    """Return 'J. Smith' format. Protects full name from logs."""
    if not last:
        return ""
    initial = f"{first[0]}. " if first else ""
    return f"{initial}{last}"


def mask_doc_number(doc_number: str | None) -> str | None:
    if not doc_number:
        return None
    return f"****{doc_number[-4:]}" if len(doc_number) >= 4 else "****"


def scrub_pii_from_string(text: str) -> str:
    """Best-effort PII scrub for log strings. Not a security boundary."""
    text = _DOB_RE.sub("[DOB_REDACTED]", text)
    text = _DOC_NUM_RE.sub(r"\1****", text)
    return text
