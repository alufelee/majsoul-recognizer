"""GUI 测试共享 fixtures

仅注册 needs_tk marker 供 Spec C 中 tkinter 相关测试使用。
"""
import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "needs_tk: test requires tkinter")
