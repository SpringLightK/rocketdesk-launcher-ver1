# app_launcher/core/desktop_scanner.py
# -*- coding: utf-8 -*-

import os
from pathlib import Path
from typing import List, Tuple

try:
    import win32com.client  # 用来解析 .lnk 快捷方式
except ImportError:
    win32com = None


def _get_possible_desktop_dirs() -> List[Path]:
    """
    返回可能的“桌面”目录列表：
    - 当前用户 Desktop / 桌面
    - 公共桌面 C:\\Users\\Public\\Desktop
    - OneDrive Desktop / 桌面（如果存在）
    """
    dirs: List[Path] = []
    home = Path.home()

    # 当前用户桌面（英文 / 中文）
    for name in ["Desktop", "桌面"]:
        p = home / name
        if p.is_dir():
            dirs.append(p)

    # 公共桌面
    public_root = Path(os.environ.get("PUBLIC", r"C:\Users\Public"))
    public_desktop = public_root / "Desktop"
    if public_desktop.is_dir():
        dirs.append(public_desktop)

    # OneDrive 桌面
    onedrive_root = os.environ.get("OneDrive")
    if onedrive_root:
        onedrive_root = Path(onedrive_root)
        for name in ["Desktop", "桌面"]:
            p = onedrive_root / name
            if p.is_dir():
                dirs.append(p)

    # 去重
    unique_dirs = []
    seen = set()
    for d in dirs:
        dp = d.resolve()
        if dp not in seen:
            seen.add(dp)
            unique_dirs.append(dp)

    return unique_dirs


def _resolve_lnk(path: Path) -> Path:
    """
    如果是 .lnk，尝试解析真实目标路径。
    - 成功：返回目标（可能是 exe、文件夹、别的文件）
    - 失败：返回原 .lnk 本身
    """
    if win32com is None:
        return path

    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(path))
        target = shortcut.Targetpath
        if target:
            target_path = Path(target)
            if target_path.exists():
                return target_path
    except Exception:
        pass
    return path


def scan_desktop_executables() -> List[Tuple[str, str]]:
    """
    扫描所有可能的“桌面”目录，返回【能打开的路径】列表。

    返回：
        [(显示名称, 真实路径), ...]

    - 显示名称：直接用文件 / 文件夹名字（不去扩展名）
    - 包括：
        * 文件夹
        * 任意文件
        * .lnk 快捷方式（尽量解析成真实目标）
    - 使用 os.startfile(path) 即可打开
    """
    candidates: List[Tuple[str, str]] = []
    seen_paths = set()

    desktop_dirs = _get_possible_desktop_dirs()
    if not desktop_dirs:
        return candidates

    for desktop in desktop_dirs:
        # 遍历桌面以及子目录的所有内容
        for root, dirs, files in os.walk(desktop):
            root_path = Path(root)

            # 1) 先处理文件夹本身（可以打开）
            for dname in dirs:
                dpath = root_path / dname
                real_path = dpath.resolve()
                real_path_str = str(real_path)
                if real_path_str in seen_paths:
                    continue
                seen_paths.add(real_path_str)

                display_name = dpath.name  # 文件夹名，完整保留
                candidates.append((display_name, real_path_str))

            # 2) 再处理文件（包括 .lnk）
            for fname in files:
                fpath = root_path / fname
                lower = fname.lower()

                # 如果是 .lnk，尽量解析真实目标
                if lower.endswith(".lnk"):
                    real_path = _resolve_lnk(fpath).resolve()
                    if not real_path.exists():
                        # 目标不存在就直接跳过
                        continue
                else:
                    real_path = fpath.resolve()

                real_path_str = str(real_path)
                if real_path_str in seen_paths:
                    continue
                seen_paths.add(real_path_str)

                display_name = fpath.name  # 文件名，含扩展名
                candidates.append((display_name, real_path_str))

    return candidates
