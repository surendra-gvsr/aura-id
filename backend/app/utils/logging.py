import logging
import structlog
from app.utils.pii import scrub_pii_from_string


def _pii_scrub_processor(logger, method, event_dict):
    """structlog processor — scrubs PII from every log line before output."""
    for key in ("first_name", "last_name", "dob", "doc_number", "email", "phone"):
        event_dict.pop(key, None)
    if isinstance(event_dict.get("event"), str):
        event_dict["event"] = scrub_pii_from_string(event_dict["event"])
    return event_dict


def configure_structlog(environment: str = "development") -> None:
    """Configure structlog. Call once at app startup with the current environment."""
    log_level = logging.DEBUG if environment != "production" else logging.INFO
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _pii_scrub_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
