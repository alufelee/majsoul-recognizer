"""校准工具测试"""

from pathlib import Path

import cv2
import numpy as np
import pytest

from majsoul_recognizer.calibrate import calibrate, draw_zones_on_image

FIXTURES = Path(__file__).parent / "fixtures"
CONFIG = Path(__file__).parent.parent / "config" / "zones.yaml"


class TestCalibrate:
    """校准工具测试"""

    def test_draw_zones_on_synthetic_image(self, sample_screenshot):
        """在合成图像上绘制区域框"""
        result = draw_zones_on_image(sample_screenshot, CONFIG)
        assert result.shape == sample_screenshot.shape
        # 标注图应与原图不同（有绘制内容）
        assert not np.array_equal(result, sample_screenshot)

    def test_draw_zones_with_real_screenshot(self):
        """用真实截图校验区域框绘制"""
        screenshot = FIXTURES / "majsoul_screenshot.png"
        if not screenshot.exists():
            pytest.skip("Real screenshot not available yet")

        image = cv2.imread(str(screenshot))
        assert image is not None

        result = draw_zones_on_image(image, CONFIG)
        assert result.shape[:2] == image.shape[:2]

    def test_calibrate_saves_preview(self, sample_screenshot, tmp_path):
        """calibrate 输出预览图文件"""
        screenshot_path = tmp_path / "test.png"
        cv2.imwrite(str(screenshot_path), sample_screenshot)

        output = calibrate(str(screenshot_path), str(CONFIG))
        assert output is not None
        assert Path(output).exists()
        assert Path(output).stat().st_size > 0
