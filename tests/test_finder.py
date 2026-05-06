"""窗口发现测试"""

from majsoul_recognizer.capture.finder import (
    WindowInfo,
    WindowFinder,
    create_finder,
)


class TestWindowInfo:
    """窗口信息数据结构测试"""

    def test_create_window_info(self):
        info = WindowInfo(title="Mahjong Soul", x=0, y=0, width=1920, height=1080)
        assert info.title == "Mahjong Soul"
        assert info.width == 1920

    def test_window_info_is_valid(self):
        valid = WindowInfo(title="Mahjong Soul", x=0, y=0, width=1920, height=1080)
        assert valid.is_valid is True

        zero_size = WindowInfo(title="test", x=0, y=0, width=0, height=0)
        assert zero_size.is_valid is False


class TestWindowFinder:
    """窗口发现接口测试 (mock 测试)"""

    def test_create_finder_returns_instance(self):
        finder = create_finder()
        assert isinstance(finder, WindowFinder)

    def test_finder_has_find_method(self):
        finder = create_finder()
        assert hasattr(finder, "find_window")

    def test_finder_target_titles(self):
        finder = create_finder()
        assert len(finder.target_keywords) > 0
