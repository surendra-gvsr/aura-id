# agent/tests/test_typer.py
import pytest
from unittest.mock import patch, MagicMock
from src.models import ScanData
from src.pms_profiles.loader import PmsProfile, FieldAction
from src.typer import TyperEngine, TyperError


def _profile(fields: list[tuple[str, str]]) -> PmsProfile:
    return PmsProfile(
        name="Test", window_title_regex=".*Test.*",
        field_order=[FieldAction(field=f, post_action=pa) for f, pa in fields],
        pre_typing_delay_ms=0, inter_field_delay_ms=0, max_duration_ms=10000,
    )


def _scan(**kw) -> ScanData:
    base = dict(scan_id="s1", pms_profile_name="test", last_name="Smith",
                first_name="John", dob="1990-01-15", doc_number="A12345678",
                address_line_1="123 Main St", city="Springfield",
                postal_code="12345", email="j@h.com")
    base.update(kw)
    return ScanData(**base)


class TestTyperEngine:
    @patch("src.typer.time")
    @patch("src.typer.pyautogui")
    def test_types_fields_in_order(self, mock_pag, mock_time):
        profile = _profile([("last_name", "tab"), ("first_name", "tab")])
        engine = TyperEngine()
        engine.type_scan(_scan(), profile)
        typed = [c.args[0] for c in mock_pag.typewrite.call_args_list]
        assert typed == ["Smith", "John"]

    @patch("src.typer.time")
    @patch("src.typer.pyautogui")
    def test_presses_tab_between_fields(self, mock_pag, mock_time):
        profile = _profile([("last_name", "tab"), ("first_name", "tab")])
        TyperEngine().type_scan(_scan(), profile)
        hotkeys = [c.args[0] for c in mock_pag.hotkey.call_args_list]
        assert hotkeys.count("tab") == 2

    @patch("src.typer.time")
    @patch("src.typer.pyautogui")
    def test_presses_enter_on_last_field(self, mock_pag, mock_time):
        profile = _profile([("last_name", "tab"), ("email", "enter")])
        TyperEngine().type_scan(_scan(), profile)
        hotkeys = [c.args[0] for c in mock_pag.hotkey.call_args_list]
        assert hotkeys[-1] == "enter"

    @patch("src.typer.time")
    @patch("src.typer.pyautogui")
    def test_skips_none_fields(self, mock_pag, mock_time):
        profile = _profile([("last_name", "tab"), ("address_line_2", "tab")])
        TyperEngine().type_scan(_scan(address_line_2=None), profile)
        typed = [c.args[0] for c in mock_pag.typewrite.call_args_list]
        assert typed == ["Smith"]  # address_line_2 is None — skipped

    @patch("src.typer.time")
    @patch("src.typer.pyautogui")
    def test_failsafe_always_true(self, mock_pag, mock_time):
        TyperEngine().type_scan(_scan(), _profile([("last_name", "tab")]))
        assert mock_pag.FAILSAFE is True

    @patch("src.typer.time")
    @patch("src.typer.pyautogui")
    def test_reformats_dob_to_mm_dd_yyyy(self, mock_pag, mock_time):
        from src.pms_profiles.loader import FieldAction, PmsProfile
        profile = PmsProfile(
            name="T", window_title_regex=".*",
            field_order=[FieldAction(field="dob", post_action="tab", format="MM/DD/YYYY")],
            pre_typing_delay_ms=0, inter_field_delay_ms=0, max_duration_ms=10000,
        )
        TyperEngine().type_scan(_scan(dob="1990-01-15"), profile)
        typed = [c.args[0] for c in mock_pag.typewrite.call_args_list]
        assert typed[0] == "01/15/1990"

    @patch("src.typer.time")
    @patch("src.typer.pyautogui")
    def test_raises_typer_error_when_max_duration_exceeded(self, mock_pag, mock_time):
        from src.typer import TyperError
        profile = _profile([("last_name", "tab")])
        profile.max_duration_ms = -1  # always exceeded
        with pytest.raises(TyperError, match="max_duration_exceeded"):
            TyperEngine().type_scan(_scan(), profile)
