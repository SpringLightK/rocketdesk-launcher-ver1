# app_launcher/core/config_store.py
# -*- coding: utf-8 -*-
import json
import os
from typing import List, Dict

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "apps_config.json"
)


class AppConfigStore:
    """
    管理 app 配置（原始名称 + 路径 + 别名列表）

    apps 结构：
    {
      "apps": [
        {
          "id": "wechat",
          "exe_path": "C:/xx/WeChat.exe",
          "base_name": "微信",                  # 原始名称（显示用）
          "aliases": ["微信", "weixin", "웨이신"]  # 所有别名（包含 base_name）
        },
        ...
      ]
    }
    """

    def __init__(self, config_path: str = None):
        self.config_path = os.path.abspath(config_path or DEFAULT_CONFIG_PATH)
        self.apps: List[Dict] = []
        self.load()

    def load(self):
        """从 JSON 文件加载配置"""
        if not os.path.exists(self.config_path):
            self.apps = []
            return
        with open(self.config_path, "r", encoding="utf-8") as f:
            try:
                cfg = json.load(f)
            except json.JSONDecodeError:
                cfg = {"apps": []}
        # 确保每条记录都有 base_name / aliases 字段
        self.apps = []
        for app in cfg.get("apps", []):
            base_name = app.get("base_name")
            aliases = app.get("aliases") or []
            # 兼容旧结构：只有 aliases[0] 没有 base_name 的情况
            if base_name is None:
                if aliases:
                    base_name = aliases[0]
                else:
                    base_name = app.get("id", "")
            # 确保 base_name 在 aliases 里
            if base_name and base_name not in aliases:
                aliases.insert(0, base_name)
            self.apps.append({
                "id": app.get("id", base_name),
                "exe_path": app.get("exe_path", ""),
                "base_name": base_name,
                "aliases": aliases,
            })

    def save(self):
        """把 apps 写回 JSON 文件"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"apps": self.apps}, f, ensure_ascii=False, indent=2)

    def add_app(self, app_id: str, exe_path: str, base_name: str):
        """添加一条新记录，初始别名只有 base_name 一个"""
        self.apps.append({
            "id": app_id,
            "exe_path": exe_path,
            "base_name": base_name,
            "aliases": [base_name] if base_name else [],
        })

    def delete_app(self, app_index: int):
        """按索引删一条记录"""
        if 0 <= app_index < len(self.apps):
            self.apps.pop(app_index)

    def update_app(self, index: int, base_name: str, exe_path: str):
        """更新原始名称和路径（别名列表保留）"""
        if index < 0 or index >= len(self.apps):
            return
        app = self.apps[index]
        app["exe_path"] = exe_path
        old_base = app.get("base_name", "")
        app["base_name"] = base_name
        aliases = app.get("aliases", [])
        # 把老的 base_name 替换成新的
        if old_base in aliases:
            aliases[aliases.index(old_base)] = base_name
        elif base_name and base_name not in aliases:
            aliases.insert(0, base_name)
        app["aliases"] = aliases

    def add_alias(self, index: int, alias: str):
        """给某个 app 添加一个自定义别名"""
        if index < 0 or index >= len(self.apps):
            return
        alias = alias.strip()
        if not alias:
            return
        app = self.apps[index]
        aliases = app.get("aliases", [])
        if alias not in aliases:
            aliases.append(alias)
            app["aliases"] = aliases

    def remove_alias(self, index: int, alias: str):
        """从某个 app 的别名列表里删除一个别名（base_name 不允许删）"""
        if index < 0 or index >= len(self.apps):
            return
        app = self.apps[index]
        base_name = app.get("base_name", "")
        if alias == base_name:
            # 原始名称不允许删除
            return
        aliases = app.get("aliases", [])
        if alias in aliases:
            aliases.remove(alias)
            app["aliases"] = aliases
