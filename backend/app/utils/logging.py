import logging
import structlog
from app.utils.pii import scrub_pii_from_string


def _pii_scrub_processor(logger, method, event_dict):
    """structlog processor — scrubs PII from every log line before output."""
    for key in ("first_name", "last_name", "dob", "doc_number", "email", "phone"):
        if key in event_dict:
            del event_dict[key]
    if "event" in event_dict and isinstance(event_dict["event"], str):
        event_dict["event"] = scrub_pii_from_string(event_dict["event"])
    return event_dict


def configure_structlog() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _pii_scrub_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
