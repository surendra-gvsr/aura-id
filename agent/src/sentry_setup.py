# agent/src/sentry_setup.py
import re
import sentry_sdk
from sentry_sdk.integrations.threading import ThreadingIntegration

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PII_KEYS = frozenset({
    "first_name", "last_name", "dob", "email", "doc_number",
    "address_line_1", "address_line_2", "city", "postal_code", "parsed_data",
})


def _scrub(d: dict) -> dict:
    result = {}
    for k, v in d.items():
        if k in _PII_KEYS:
            continue
        if isinstance(v, str):
            v = _EMAIL_RE.sub("[REDACTED]", v)
        result[k] = v
    return result


def scrub_sentry_event(event: dict, hint: dict) -> dict:
    """before_send hook — strips PII from all sections of a Sentry event."""
    if "extra" in event:
        event["extra"] = _scrub(event["extra"])
    if "tags" in event:
        event["tags"] = _scrub(event["tags"])
    try:
        for exc_val in event.get("exception", {}).get("values", []):
            for frame in exc_val.get("stacktrace", {}).get("frames", []):
                if "vars" in frame:
                    frame["vars"] = _scrub(frame["vars"])
    except (KeyError, TypeError):
        pass
    return event


def init_sentry(dsn: str, release: str) -> None:
    if not dsn or not dsn.strip():
        return
    sentry_sdk.init(
        dsn=dsn,
        release=release,
        send_default_pii=False,
        before_send=scrub_sentry_event,
        integrations=[ThreadingIntegration(propagate_hub=False)],
        traces_sample_rate=0.0,
    )
