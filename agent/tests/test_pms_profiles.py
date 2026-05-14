# agent/tests/test_pms_profiles.py
import pytest
from pathlib import Path
from src.pms_profiles.loader import ProfileLoader, PmsProfile, ProfileNotFoundError

PROFILES_DIR = Path(__file__).parent.parent / "src" / "pms_profiles"


class TestProfileLoader:
    def test_loads_opera_profile(self):
        loader = ProfileLoader(PROFILES_DIR)
        p = loader.get("opera")
        assert p.name == "Opera PMS"
        assert len(p.field_order) >= 6

    def test_profile_has_window_regex(self):
        p = ProfileLoader(PROFILES_DIR).get("opera")
        assert p.window_title_regex

    def test_field_order_items_have_required_keys(self):
        p = ProfileLoader(PROFILES_DIR).get("opera")
        for fa in p.field_order:
            assert fa.field
            assert fa.action in ("type", "skip")
            assert fa.post_action in ("tab", "enter", "none")

    def test_unknown_profile_raises(self):
        with pytest.raises(ProfileNotFoundError):
            ProfileLoader(PROFILES_DIR).get("nonexistent_pms")

    def test_match_window_returns_opera_for_opera_title(self):
        p = ProfileLoader(PROFILES_DIR).match_window("Opera PMS - Reservation")
        assert p is not None
        assert p.name == "Opera PMS"

    def test_match_window_returns_none_for_notepad(self):
        loader = ProfileLoader(PROFILES_DIR)
        p = loader.match_window("Notepad - Untitled")
        assert p is None

    def test_all_five_profiles_load(self):
        loader = ProfileLoader(PROFILES_DIR)
        for name in ["opera", "synxis", "cloudbeds", "hotelkey", "generic"]:
            assert loader.get(name) is not None
