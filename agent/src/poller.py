# agent/src/poller.py
import threading
import requests
import structlog
from src.models import ScanData

log = structlog.get_logger()

_PII_FIELDS = {
    "last_name", "first_name", "dob", "doc_number",
    "address_line_1", "address_line_2", "city", "postal_code", "email",
}


class Poller:
    def __init__(self, api_base: str, token: str, interval: int = 3) -> None:
        self._api_base = api_base.rstrip("/")
        self._interval = interval
        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {token}"

    def fetch_pending(self) -> ScanData | None:
        """GET /scans/pending-type — returns ScanData or None."""
        try:
            r = self._session.get(
                f"{self._api_base}/scans/pending-type",
                timeout=(5, 10),
            )
        except requests.RequestException as exc:
            log.warning("poll.error", reason=str(exc)[:60])
            return None
        if r.status_code == 204 or not r.content:
            return None
        if not r.ok:
            log.warning("poll.http_error", status=r.status_code)
            return None
        data = r.json()
        fields = data.get("fields", {})
        allowed = {k: v for k, v in fields.items() if k in _PII_FIELDS}
        return ScanData(
            scan_id=data["scan_id"],
            pms_profile_name=data["pms_profile_name"],
            **allowed,
        )

    def mark_typed(self, scan_id: str, *, status: str, duration_ms: int) -> None:
        """POST /scans/{scan_id}/mark-typed — audit trail, no PII."""
        try:
            self._session.post(
                f"{self._api_base}/scans/{scan_id}/mark-typed",
                json={"status": status, "duration_ms": duration_ms},
                timeout=(5, 10),
            )
            log.info("typed", scan_id=scan_id, status=status, duration_ms=duration_ms)
        except requests.RequestException as exc:
            log.warning("mark_typed.error", scan_id=scan_id, reason=str(exc)[:60])

    def run_loop(
        self,
        on_scan_ready,
        stop_event: threading.Event,
    ) -> None:
        """Background poll loop. Calls on_scan_ready(ScanData) when a scan arrives."""
        while not stop_event.is_set():
            scan = self.fetch_pending()
            if scan is not None:
                log.info("poll.scan_pending", scan_id=scan.scan_id, profile=scan.pms_profile_name)
                on_scan_ready(scan)
            stop_event.wait(self._interval)
