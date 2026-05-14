# agent/tests/test_tray.py
import pytest
from unittest.mock import MagicMock, patch
from src.tray import TrayState, TrayApp


class TestTrayState:
    def test_five_states_defined(self):
        expected = {"idle", "waiting", "typing", "error", "subscription_inactive"}
        actual = {s.value for s in TrayState}
        assert actual == expected


class TestTrayApp:
    @patch("src.tray.pystray")
    @patch("src.tray.Image")
    def test_initial_state_is_idle(self, mock_img, mock_pystray):
        mock_pystray.Icon.return_value = MagicMock()
        app = TrayApp(on_quit=lambda: None)
        assert app.state == TrayState.IDLE

    @patch("src.tray.pystray")
    @patch("src.tray.Image")
    def test_set_state_updates_state_attribute(self, mock_img, mock_pystray):
        mock_icon = MagicMock()
        mock_pystray.Icon.return_value = mock_icon
        app = TrayApp(on_quit=lambda: None)
        app.icon = mock_icon
        app.set_state(TrayState.WAITING)
        assert app.state == TrayState.WAITING

    @patch("src.tray.pystray")
    @patch("src.tray.Image")
    def test_notify_calls_icon_notify(self, mock_img, mock_pystray):
        mock_icon = MagicMock()
        mock_pystray.Icon.return_value = mock_icon
        app = TrayApp(on_quit=lambda: None)
        app.icon = mock_icon
        app.notify("Test message")
        mock_icon.notify.assert_called_once_with("Aura ID", "Test message")

    @patch("src.tray.pystray")
    @patch("src.tray.Image")
    def test_notify_silent_when_no_icon(self, mock_img, mock_pystray):
        mock_pystray.Icon.return_value = MagicMock()
        app = TrayApp(on_quit=lambda: None)
        app.icon = None
        app.notify("Should not raise")
