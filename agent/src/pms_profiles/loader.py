# agent/src/pms_profiles/loader.py
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


class ProfileNotFoundError(Exception):
    pass


@dataclass
class FieldAction:
    field: str
    action: str = "type"
    post_action: str = "tab"
    format: str | None = None


@dataclass
class PmsProfile:
    name: str
    window_title_regex: str
    field_order: list[FieldAction]
    pre_typing_delay_ms: int = 150
    inter_field_delay_ms: int = 80
    fail_safe_corner: bool = True
    max_duration_ms: int = 10000
    _re: re.Pattern | None = field(default=None, init=False, repr=False, compare=False, hash=False)

    def matches_window(self, title: str) -> bool:
        if self._re is None:
            self._re = re.compile(self.window_title_regex, re.IGNORECASE)
        return bool(self._re.search(title))


class ProfileLoader:
    def __init__(self, profiles_dir: Path) -> None:
        self._dir = profiles_dir
        self._cache: dict[str, PmsProfile] = {}

    def get(self, name: str) -> PmsProfile:
        if name in self._cache:
            return self._cache[name]
        path = self._dir / f"{name}.json"
        if not path.exists():
            raise ProfileNotFoundError(f"No profile file: {name}.json")
        with path.open() as f:
            data = json.load(f)
        profile = PmsProfile(
            name=data["name"],
            window_title_regex=data["window_title_regex"],
            field_order=[
                FieldAction(
                    field=fa["field"],
                    action=fa.get("action", "type"),
                    post_action=fa.get("post_action", "tab"),
                    format=fa.get("format"),
                )
                for fa in data["field_order"]
            ],
            pre_typing_delay_ms=data.get("pre_typing_delay_ms", 150),
            inter_field_delay_ms=data.get("inter_field_delay_ms", 80),
            fail_safe_corner=data.get("fail_safe_corner", True),
            max_duration_ms=data.get("max_duration_ms", 10000),
        )
        self._cache[name] = profile
        return profile

    def match_window(self, window_title: str) -> PmsProfile | None:
        """Return first non-generic profile whose regex matches the window title."""
        for json_file in sorted(self._dir.glob("*.json")):
            if json_file.stem == "generic":
                continue
            try:
                profile = self.get(json_file.stem)
                if profile.matches_window(window_title):
                    return profile
            except Exception:
                pass
        return None
