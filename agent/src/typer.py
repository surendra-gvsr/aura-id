# agent/src/typer.py
import time
from time import monotonic as _monotonic
from datetime import datetime
import pyautogui
import structlog
from src.models import ScanData
from src.pms_profiles.loader import PmsProfile

log = structlog.get_logger()

_DOB_TARGET_FMTS = {
    "MM/DD/YYYY": "%m/%d/%Y",
    "DD/MM/YYYY": "%d/%m/%Y",
    "YYYY-MM-DD": "%Y-%m-%d",
    "MM-DD-YYYY": "%m-%d-%Y",
}
_DOB_SOURCE_FMTS = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y"]


def _reformat_dob(dob_str: str, target_fmt_key: str) -> str:
    target_fmt = _DOB_TARGET_FMTS.get(target_fmt_key)
    if not target_fmt:
        return dob_str
    for src in _DOB_SOURCE_FMTS:
        try:
            return datetime.strptime(dob_str, src).strftime(target_fmt)
        except ValueError:
            continue
    return dob_str


class TyperError(Exception):
    pass


class TyperEngine:
    def type_scan(self, scan: ScanData, profile: PmsProfile) -> int:
        """
        Type scan fields per profile. Returns duration_ms.
        Raises TyperError if the hard cap is exceeded.
        """
        pyautogui.FAILSAFE = True
        time.sleep(profile.pre_typing_delay_ms / 1000)
        start = _monotonic()

        for fa in profile.field_order:
            elapsed_ms = (_monotonic() - start) * 1000
            if elapsed_ms > profile.max_duration_ms:
                raise TyperError("max_duration_exceeded")

            value = getattr(scan, fa.field, None)
            if value is None:
                continue

            if fa.field == "dob" and fa.format:
                value = _reformat_dob(value, fa.format)

            pyautogui.typewrite(str(value), interval=0.03)

            if fa.post_action == "tab":
                pyautogui.hotkey("tab")
            elif fa.post_action == "enter":
                pyautogui.hotkey("enter")

            time.sleep(profile.inter_field_delay_ms / 1000)

        return int((_monotonic() - start) * 1000)
