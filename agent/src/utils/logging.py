# agent/src/utils/logging.py
import re
import sys
from typing import Any

import structlog

# Scope: expects normalized plaintext from the backend's structured JSON API.
# Encoded forms (percent-encoding, HTML entities) are the backend's responsibility.

# Compiled regex patterns for PII detection
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_DOB_RE = re.compile(r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b")
_DOC_NUM_RE = re.compile(r"\b[A-Za-z]{1,3}\d{6,12}\b")

# Known PII field names — any event containing these keys is dropped
_PII_KEYS = frozenset(
    {
        "first_name",
        "last_name",
        "dob",
        "email",
        "doc_number",
        "address_line_1",
        "address_line_2",
        "city",
        "postal_code",
        "parsed_data",
        "fields_data",
        "token",
        "workstation_token",
    }
)

# Standard structlog keys exempt from the long-value length check
_SAFE_LONG_KEYS = frozenset({"event", "level", "timestamp", "logger"})

# String values longer than this in non-standard keys are considered suspicious
_SUSPICIOUS_LEN = 40


def _is_pii_string(value: str) -> bool:
    """Return True if the string matches any known PII pattern."""
    if _EMAIL_RE.search(value):
        return True
    if _DOB_RE.search(value):
        return True
    if _DOC_NUM_RE.search(value):
        return True
    return False


def pii_scrub_processor(logger: Any, method: str, event_dict: dict) -> dict:
    """structlog processor — drops any log event that contains PII.

    Raises structlog.DropEvent when the event dict contains:
    - A known PII key (first_name, email, dob, etc.)
    - An email address pattern in any string value
    - A DOB-like date pattern in any string value
    - A document number pattern in any string value
    - A non-standard key whose string value exceeds _SUSPICIOUS_LEN characters
    """
    for key, value in event_dict.items():
        # Drop immediately if a known PII key is present
        if key in _PII_KEYS:
            raise structlog.DropEvent()

        if isinstance(value, str):
            # Check string value for PII patterns
            if _is_pii_string(value):
                raise structlog.DropEvent()
            # Long values in non-standard keys are suspicious
            if key not in _SAFE_LONG_KEYS and len(value) > _SUSPICIOUS_LEN:
                raise structlog.DropEvent()

    return event_dict


def configure_logging(log_file: str | None = None) -> None:
    """Configure structlog with the PII scrubbing processor.

    Args:
        log_file: Optional path to write logs to. Defaults to stdout.
    """
    # Only configure once — structlog is global state.
    # Re-calling with a different log_file has no effect after first call.
    if structlog.is_configured():
        return
    _log_fh = open(log_file, "a") if log_file else sys.stdout  # noqa: SIM115
    processors = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        pii_scrub_processor,
        structlog.processors.JSONRenderer(),
    ]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=_log_fh),
    )
