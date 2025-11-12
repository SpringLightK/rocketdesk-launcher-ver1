# app_launcher/utils/resources.py
# -*- coding: utf-8 -*-
"""
统一管理资源路径（图标 / 配置），兼容：
- 开发环境：python -m app_launcher.main
- PyInstaller 打包后的 exe（onefile/onedir）
"""

from pathlib import Path
import sys


def _app_root() -> Path:
    """
    返回资源根目录：

    开发环境：
        .../winapptool/app_launcher

    exe 环境 (PyInstaller)：
        .../MEIPASS/app_launcher

    这样在两种环境下：
        resource_path("img/app_icon.ico")
    都指向 app_launcher/img/app_icon.ico 这一套目录。
    """
    # 打包后的 exe 运行时，PyInstaller 会设置 sys.frozen + sys._MEIPASS
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # MEIPASS 是解压根目录，我们再加一层 app_launcher
        return Path(sys._MEIPASS) / "app_launcher"

    # 源码环境：当前文件在 app_launcher/utils 下，往上一层就是 app_launcher
    return Path(__file__).resolve().parents[1]


def resource_path(relative_path: str) -> str:
    """
    获取资源绝对路径。

    约定：relative_path 还是像你之前那样写：
        "img/app_icon.ico"
        "config/apps_config.json"

    开发环境：
        -> <项目根>/app_launcher/img/...
           <项目根>/app_launcher/config/...

    exe 环境：
        -> <MEIPASS>/app_launcher/img/...
           <MEIPASS>/app_launcher/config/...
    """
    base = _app_root()
    return str(base / relative_path)
