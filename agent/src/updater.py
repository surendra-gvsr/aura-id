# agent/src/updater.py
from dataclasses import dataclass
import requests
import structlog

log = structlog.get_logger()


def _ver(v: str) -> tuple[int, ...]:
    """Parse semver string to comparable tuple. Returns (0,) on error."""
    try:
        return tuple(int(x) for x in v.split("."))
    except (ValueError, AttributeError):
        return (0,)


@dataclass
class UpdateInfo:
    update_available: bool
    latest_version: str = ""
    download_url: str = ""
    notes: str = ""


class UpdateChecker:
    def __init__(self, check_url: str, current_version: str) -> None:
        self._url = check_url
        self._current = current_version

    def check(self) -> UpdateInfo:
        try:
            r = requests.get(self._url, timeout=(5, 10))
            r.raise_for_status()
            data = r.json()
        except (requests.RequestException, ValueError, KeyError) as exc:
            log.warning("updater.check_failed", reason=str(exc)[:200])
            return UpdateInfo(update_available=False)

        latest = data.get("version", "0.0.0")
        url = data.get("url", "")
        if url and not url.startswith("https://dl.auraid.com/"):
            log.warning("updater.untrusted_url")
            url = ""
        return UpdateInfo(
            update_available=_ver(latest) > _ver(self._current),
            latest_version=latest,
            download_url=url,
            notes=data.get("notes", ""),
        )
