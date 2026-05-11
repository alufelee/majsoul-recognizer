"""Theme system tests — Catppuccin Mocha / Latte"""

from majsoul_recognizer.gui.theme import Theme, get_theme

NEW_KEYS = {
    "bg_base", "bg_mantle", "bg_surface0", "bg_surface1", "bg_crust",
    "fg_primary", "fg_secondary", "fg_muted",
    "accent", "accent_dim",
    "green", "peach", "red",
    "blue", "yellow", "mauve", "teal",
    "lavender", "sky", "flamingo",
    "surface_hover",
}


class TestThemeColors:
    def test_dark_has_all_keys(self):
        assert set(Theme.DARK.keys()) == NEW_KEYS

    def test_light_has_all_keys(self):
        assert set(Theme.LIGHT.keys()) == NEW_KEYS

    def test_dark_and_light_have_same_keys(self):
        assert set(Theme.DARK.keys()) == set(Theme.LIGHT.keys())

    def test_all_values_are_hex_colors(self):
        for name, colors in [("DARK", Theme.DARK), ("LIGHT", Theme.LIGHT)]:
            for key, value in colors.items():
                assert value.startswith("#"), f"{name}.{key} = {value!r}"
                assert len(value) == 7, f"{name}.{key} = {value!r}"


class TestGetTheme:
    def test_get_dark(self):
        result = get_theme("dark")
        assert result == Theme.DARK

    def test_get_light(self):
        result = get_theme("light")
        assert result == Theme.LIGHT

    def test_get_unknown_returns_dark(self):
        result = get_theme("unknown")
        assert result == Theme.DARK

    def test_returns_copy_not_reference(self):
        result = get_theme("dark")
        result["accent"] = "#CHANGED"
        assert Theme.DARK["accent"] == "#89b4fa"

    def test_light_returns_copy_not_reference(self):
        result = get_theme("light")
        result["accent"] = "#CHANGED"
        assert Theme.LIGHT["accent"] == "#1e66f5"
