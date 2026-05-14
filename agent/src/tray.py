# agent/src/tray.py
import enum
from typing import Callable

import pystray
from PIL import Image, ImageDraw

# RGB colors keyed by state value
_STATE_COLORS: dict[str, tuple[int, int, int]] = {
    "idle": (70, 130, 180),
    "waiting": (255, 165, 0),
    "typing": (50, 205, 50),
    "error": (220, 20, 60),
    "subscription_inactive": (128, 0, 0),
}


class TrayState(enum.Enum):
    """Five possible states for the system tray icon."""

    IDLE = "idle"
    WAITING = "waiting"
    TYPING = "typing"
    ERROR = "error"
    SUBSCRIPTION_INACTIVE = "subscription_inactive"


def _make_icon_image(state: TrayState) -> Image.Image:
    """Create a 64x64 RGBA image with a filled circle for the given state."""
    color = _STATE_COLORS[state.value]
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse([4, 4, 60, 60], fill=color)
    return img


class TrayApp:
    """Manages the pystray system tray icon and its 5 status states."""

    def __init__(self, on_quit: Callable[[], None]) -> None:
        # Start in idle state; icon is created when run() is called
        self.state: TrayState = TrayState.IDLE
        self._on_quit = on_quit
        self.icon: pystray.Icon | None = None

    def _build_menu(self) -> pystray.Menu:
        """Build the right-click context menu for the tray icon."""
        return pystray.Menu(
            pystray.MenuItem("Aura ID Agent", None, enabled=False),
            pystray.MenuItem(f"Status: {self.state.value}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Quit",
                lambda icon, _: (icon.stop(), self._on_quit()),
            ),
        )

    def set_state(self, state: TrayState) -> None:
        """Update the tray icon color and menu to reflect the new state."""
        self.state = state
        if self.icon:
            self.icon.icon = _make_icon_image(state)
            self.icon.menu = self._build_menu()

    def notify(self, message: str) -> None:
        """Show a system notification balloon. No-op when icon is not running."""
        if self.icon:
            self.icon.notify("Aura ID", message)

    def run(self) -> None:
        """Create and run the tray icon (blocks until quit)."""
        self.icon = pystray.Icon(
            "aura-id",
            _make_icon_image(TrayState.IDLE),
            "Aura ID Agent",
            self._build_menu(),
        )
        self.icon.run()
