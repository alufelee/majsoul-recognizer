"""GUI 包入口

[C1 修复] tkinter 检测仅在 main() 中执行，不影响子模块导入。
纯逻辑模块（settings, worker, theme, app_state）可在无 tkinter 环境下正常导入和测试。
"""


def main() -> None:
    """启动 GUI 主窗口"""
    try:
        import tkinter  # noqa: F401
    except ImportError:
        raise SystemExit(
            "tkinter 不可用。macOS: brew install python-tk@3.14\n"
            "Windows: tkinter 随 Python 安装包自带。"
        )

    from majsoul_recognizer.gui.app import App

    app = App()
    app.run()
