# agent/src/main.py
"""Entry point — wires together all agent subsystems."""
import sys
import threading
import keyboard
import requests
import structlog

from src.config import AgentConfig
from src.models import ScanData
from src.pairing import load_token, run_pairing_dialog
from src.pii_guard import wipe
from src.pms_profiles.loader import ProfileLoader
from src.poller import Poller
from src.sentry_setup import init_sentry
from src.tray import TrayApp, TrayState
from src.typer import TyperEngine, TyperError
from src.updater import UpdateChecker
from src.utils.logging import configure_logging
from src.utils.window_detect import get_active_window_title
from pathlib import Path

log = structlog.get_logger()
_PROFILES_DIR = Path(__file__).parent / "pms_profiles"


class SubscriptionChecker:
    def __init__(self, api_base: str, token: str) -> None:
        self._url = api_base.rstrip("/") + "/hotels/me"
        self._headers = {"Authorization": f"Bearer {token}"}

    def is_active(self) -> bool:
        try:
            r = requests.get(self._url, headers=self._headers, timeout=(5, 10))
            if not r.ok:
                return False
            return r.json().get("subscription_status") == "active"
        except requests.RequestException:
            return False


class AgentApp:
    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        self._pending_scan: ScanData | None = None
        self._scan_lock = threading.Lock()
        self._stop = threading.Event()
        self._tray = TrayApp(on_quit=self._on_quit)
        self._poller = Poller(
            api_base=str(config.api_base_url),
            token=config.workstation_token,
            interval=config.poll_interval_seconds,
        )
        self._typer = TyperEngine()
        self._profiles = ProfileLoader(_PROFILES_DIR)
        self._sub = SubscriptionChecker(
            api_base=str(config.api_base_url),
            token=config.workstation_token,
        )

    def _on_quit(self) -> None:
        self._stop.set()
        with self._scan_lock:
            wipe(self._pending_scan)
            self._pending_scan = None
        sys.exit(0)

    def _on_scan_ready(self, scan: ScanData) -> None:
        with self._scan_lock:
            if self._pending_scan is not None:
                wipe(self._pending_scan)
            self._pending_scan = scan
        self._tray.set_state(TrayState.WAITING)
        self._tray.notify("Scan ready — press Ctrl+Shift+A to type")
        log.info("poll.scan_pending", scan_id=scan.scan_id, profile=scan.pms_profile_name)

    def _on_hotkey(self) -> None:
        with self._scan_lock:
            scan, self._pending_scan = self._pending_scan, None

        if scan is None:
            self._tray.notify("No scan pending")
            return

        retry = False
        try:
            if self._tray.state == TrayState.SUBSCRIPTION_INACTIVE:
                log.warning("typed", scan_id=scan.scan_id, status="failure", reason="subscription_inactive")
                return

            title = get_active_window_title()
            profile = self._profiles.match_window(title)

            if profile is None:
                log.info("typed", scan_id=scan.scan_id, status="failure", reason="window_mismatch")
                self._tray.notify("Wrong window — please focus your PMS")
                retry = True
                return

            self._tray.set_state(TrayState.TYPING)
            status, duration_ms = "failure", 0
            try:
                duration_ms = self._typer.type_scan(scan, profile)
                status = "success"
                log.info("typed", scan_id=scan.scan_id, profile_name=profile.name,
                         duration_ms=duration_ms, status="success")
            except TyperError:
                log.warning("typed", scan_id=scan.scan_id, status="failure", reason="typer_error")
                self._tray.set_state(TrayState.ERROR)
            finally:
                self._poller.mark_typed(scan.scan_id, status=status, duration_ms=duration_ms)
                if status == "success":
                    self._tray.set_state(TrayState.IDLE)
        finally:
            if retry:
                with self._scan_lock:
                    self._pending_scan = scan
            else:
                wipe(scan)

    def _subscription_loop(self) -> None:
        while not self._stop.is_set():
            active = self._sub.is_active()
            if not active:
                log.warning("subscription.inactive")
                self._tray.set_state(TrayState.SUBSCRIPTION_INACTIVE)
                self._tray.notify("Subscription inactive — contact owner")
            elif self._tray.state == TrayState.SUBSCRIPTION_INACTIVE:
                self._tray.set_state(TrayState.IDLE)
            self._stop.wait(300)

    def run(self) -> None:
        configure_logging()
        init_sentry(self._config.sentry_dsn, self._config.app_version)

        threading.Thread(
            target=self._poller.run_loop,
            args=(self._on_scan_ready, self._stop),
            daemon=True,
        ).start()

        threading.Thread(target=self._subscription_loop, daemon=True).start()

        keyboard.add_hotkey("ctrl+shift+a", self._on_hotkey)
        log.info("agent.started")
        self._tray.run()


def main() -> None:
    config = AgentConfig()
    token = load_token()
    if not token:
        token = run_pairing_dialog(str(config.api_base_url))
        if not token:
            sys.exit(0)
    config.workstation_token = token

    update_info = UpdateChecker(
        check_url=config.update_check_url,
        current_version=config.app_version,
    ).check()
    if update_info.update_available:
        log.info("update.available", version=update_info.latest_version)

    AgentApp(config).run()


if __name__ == "__main__":
    main()
