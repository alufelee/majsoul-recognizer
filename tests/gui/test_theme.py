"""主题系统测试 — 颜色定义部分（不需要 tkinter）"""

from majsoul_recognizer.gui.theme import Theme, get_theme


class TestThemeColors:
    """颜色方案完整性测试"""

    def test_dark_has_all_keys(self):
        expected_keys = {
            "bg_primary", "bg_secondary", "bg_tertiary", "bg_sidebar",
            "fg_primary", "fg_secondary", "fg_muted",
            "accent", "success", "warning", "error", "highlight",
            "border", "canvas_bg",
        }
        assert set(Theme.DARK.keys()) == expected_keys

    def test_light_has_all_keys(self):
        expected_keys = {
            "bg_primary", "bg_secondary", "bg_tertiary", "bg_sidebar",
            "fg_primary", "fg_secondary", "fg_muted",
            "accent", "success", "warning", "error", "highlight",
            "border", "canvas_bg",
        }
        assert set(Theme.LIGHT.keys()) == expected_keys

    def test_dark_and_light_have_same_keys(self):
        assert set(Theme.DARK.keys()) == set(Theme.LIGHT.keys())

    def test_all_values_are_hex_colors(self):
        for name, colors in [("DARK", Theme.DARK), ("LIGHT", Theme.LIGHT)]:
            for key, value in colors.items():
                assert value.startswith("#"), f"{name}.{key} = {value!r}, expected hex color"
                assert len(value) == 7, f"{name}.{key} = {value!r}, expected #RRGGBB format"


class TestGetTheme:
    def test_get_dark(self):
        result = get_theme("dark")
        assert result is Theme.DARK

    def test_get_light(self):
        result = get_theme("light")
        assert result is Theme.LIGHT

    def test_get_unknown_returns_dark(self):
        result = get_theme("unknown")
        assert result is Theme.DARK
