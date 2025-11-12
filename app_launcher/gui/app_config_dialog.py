# app_launcher/gui/app_config_dialog.py
# -*- coding: utf-8 -*-

from typing import List  # 类型注解（可选）
import numpy as np  # 用来构造空向量
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QHeaderView
import os
from app_launcher.core.config_store import AppConfigStore
from app_launcher.core.desktop_scanner import scan_desktop_executables
from app_launcher.core.matcher import AppMatcher

class AliasManagerDialog(QtWidgets.QDialog):
    """
    管理单个 App 的别名列表：
    - 上面是 QListWidget 展示所有别名
    - 底下有“添加别名”和“删除选中”按钮
    - base_name 不允许删除
    """

    def __init__(self, store: AppConfigStore, app_index: int, parent=None):
        super().__init__(parent)
        self.store = store
        self.app_index = app_index

        self.setWindowTitle("管理别名")
        self.resize(400, 300)

        layout = QtWidgets.QVBoxLayout(self)

        self.list_widget = QtWidgets.QListWidget()
        layout.addWidget(self.list_widget)

        # 底部按钮行
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("添加别名")
        self.btn_del = QtWidgets.QPushButton("删除选中")
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_del)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # OK / Cancel
        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        layout.addWidget(btn_box)

        # 连接信号
        self.btn_add.clicked.connect(self.on_add_alias)
        self.btn_del.clicked.connect(self.on_del_alias)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        # 初次载入列表
        self._refresh_list()

    def _refresh_list(self):
        """根据 store 里当前 app 的 aliases 刷新列表"""
        self.list_widget.clear()
        app = self.store.apps[self.app_index]
        base_name = app.get("base_name", "")
        for alias in app.get("aliases", []):
            item_text = alias
            if alias == base_name:
                item_text += "  (原始名称)"
            self.list_widget.addItem(item_text)

    def on_add_alias(self):
        """添加一个别名"""
        text, ok = QtWidgets.QInputDialog.getText(
            self, "添加别名", "请输入新的别名："
        )
        if not ok:
            return
        alias = text.strip()
        if not alias:
            return
        self.store.add_alias(self.app_index, alias)
        self._refresh_list()

    def on_del_alias(self):
        """删除选中的别名（原始名不删）"""
        cur_item = self.list_widget.currentItem()
        if cur_item is None:
            return
        text = cur_item.text()
        alias = text.split("  (原始名称)")[0]
        # 调 store 删除
        self.store.remove_alias(self.app_index, alias)
        self._refresh_list()

class AliasManagerDialog(QtWidgets.QDialog):
    """
    管理单个 App 的别名列表：
    - 上面 QListWidget 显示所有别名
    - 底部 “添加别名” / “删除选中”
    - base_name(原始名称) 不允许删除
    """

    def __init__(self, store: AppConfigStore, app_index: int, parent=None):
        super().__init__(parent)
        self.store = store
        self.app_index = app_index

        self.setWindowTitle("管理别名")
        self.resize(400, 300)

        layout = QtWidgets.QVBoxLayout(self)

        # 别名列表
        self.list_widget = QtWidgets.QListWidget()
        layout.addWidget(self.list_widget)

        # 底部按钮行
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("添加别名")
        self.btn_del = QtWidgets.QPushButton("删除选中")
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_del)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # OK / Cancel
        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        layout.addWidget(btn_box)

        # 信号
        self.btn_add.clicked.connect(self.on_add_alias)
        self.btn_del.clicked.connect(self.on_del_alias)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        # 初次加载别名
        self._refresh_list()

    def _refresh_list(self):
        """从 store 里把当前 app 的别名刷新出来"""
        self.list_widget.clear()
        app = self.store.apps[self.app_index]
        base_name = app.get("base_name", "")
        for alias in app.get("aliases", []):
            text = alias
            if alias == base_name:
                text += "  (原始名称)"
            self.list_widget.addItem(text)

    def on_add_alias(self):
        """添加别名"""
        text, ok = QtWidgets.QInputDialog.getText(
            self, "添加别名", "请输入新的别名："
        )
        if not ok:
            return
        alias = text.strip()
        if not alias:
            return
        self.store.add_alias(self.app_index, alias)
        self._refresh_list()

    def on_del_alias(self):
        """删除选中的别名（不能删原始名）"""
        item = self.list_widget.currentItem()
        if item is None:
            return
        text = item.text()
        alias = text.split("  (原始名称)")[0]
        self.store.remove_alias(self.app_index, alias)
        self._refresh_list()


# app_launcher/gui/app_config_dialog.py
# -*- coding: utf-8 -*-

import numpy as np  # 用来构造空向量
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QHeaderView

from app_launcher.core.config_store import AppConfigStore
from app_launcher.core.desktop_scanner import scan_desktop_executables
from app_launcher.core.matcher import AppMatcher


class AliasManagerDialog(QtWidgets.QDialog):
    """
    管理单个 App 的别名列表：
    - 列出所有别名
    - 可以添加 / 删除别名
    - base_name(原始名称) 不允许删除
    """

    def __init__(self, store: AppConfigStore, app_index: int, parent=None):
        super().__init__(parent)
        self.store = store
        self.app_index = app_index

        self.setWindowTitle("管理别名")
        self.resize(400, 300)

        layout = QtWidgets.QVBoxLayout(self)

        # 别名列表
        self.list_widget = QtWidgets.QListWidget()
        layout.addWidget(self.list_widget)

        # 底部按钮行
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("添加别名")
        self.btn_del = QtWidgets.QPushButton("删除选中")
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_del)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # OK / Cancel
        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        layout.addWidget(btn_box)

        # 信号
        self.btn_add.clicked.connect(self.on_add_alias)
        self.btn_del.clicked.connect(self.on_del_alias)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        # 初次加载别名
        self._refresh_list()

    def _refresh_list(self):
        """从 store 里把当前 app 的别名刷新出来"""
        self.list_widget.clear()
        app = self.store.apps[self.app_index]
        base_name = app.get("base_name", "")
        for alias in app.get("aliases", []):
            text = alias
            if alias == base_name:
                text += "  (原始名称)"
            self.list_widget.addItem(text)

    def on_add_alias(self):
        """添加别名"""
        text, ok = QtWidgets.QInputDialog.getText(
            self, "添加别名", "请输入新的别名："
        )
        if not ok:
            return
        alias = text.strip()
        if not alias:
            return
        self.store.add_alias(self.app_index, alias)
        self._refresh_list()

    def on_del_alias(self):
        """删除选中的别名（不能删原始名）"""
        item = self.list_widget.currentItem()
        if item is None:
            return
        text = item.text()
        alias = text.split("  (原始名称)")[0]
        self.store.remove_alias(self.app_index, alias)
        self._refresh_list()


class AppConfigDialog(QtWidgets.QDialog):
    """
    管理启动 App 列表的对话框：
    - 顶部：添加 + 扫描桌面 + 删除选中软件 + 初始化(清空)
    - 中间：表格（名称 + 路径），双击可修改
    - 右键名称列：管理别名... / 删除此软件
    - 底部：保存 / 取消
    """

    def __init__(self, store: AppConfigStore, matcher: AppMatcher, parent=None):
        super().__init__(parent)

        self.store = store           # 配置存储对象
        self.matcher = matcher       # 匹配器对象（里面有嵌入和缓存）
        self._updating_table = False # 标记：是否正在批量更新表格

        self.setWindowTitle("设置启动 App")
        self.resize(800, 500)

        # 普通可缩放窗口
        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.WindowMinimizeButtonHint
            | QtCore.Qt.WindowMaximizeButtonHint
            | QtCore.Qt.WindowCloseButtonHint
        )

        self._init_ui()           # 初始化界面
        self._load_from_store()   # 先把现有配置加载到表格
        #self._scan_desktop_auto() # 对话框打开时自动扫描一次桌面（追加新应用）

    def _init_ui(self):
        """初始化界面控件和布局"""
        main_layout = QtWidgets.QVBoxLayout(self)  # 根布局：垂直

        # ---------- 顶部按钮行 ----------
        top_layout = QtWidgets.QHBoxLayout()

        self.btn_add = QtWidgets.QPushButton("添加")              # 手动添加
        self.btn_scan = QtWidgets.QPushButton("扫描桌面")        # 扫描桌面
        self.btn_delete = QtWidgets.QPushButton("删除选中软件")   # ★ 新增：删除软件
        self.btn_reset = QtWidgets.QPushButton("初始化(清空)")    # 清空所有

        top_layout.addWidget(self.btn_add)
        top_layout.addWidget(self.btn_scan)
        top_layout.addWidget(self.btn_delete)
        top_layout.addWidget(self.btn_reset)
        top_layout.addStretch()

        # ---------- 中间表格 ----------
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["应用名称", "可执行路径"])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked
            | QtWidgets.QAbstractItemView.SelectedClicked
        )

        # 表格右键菜单：自定义
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.on_table_context_menu)

        # ---------- 底部按钮 ----------
        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )

        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.table)
        main_layout.addWidget(btn_box)

        # ---------- 信号 ----------
        self.btn_add.clicked.connect(self.on_add_clicked)
        self.btn_scan.clicked.connect(self.on_scan_clicked)
        self.btn_delete.clicked.connect(self.on_delete_clicked)  # 删除软件
        self.btn_reset.clicked.connect(self.on_reset_clicked)    # 初始化清空

        self.table.itemChanged.connect(self.on_item_changed)
        btn_box.accepted.connect(self.on_save)
        btn_box.rejected.connect(self.reject)

    # ====== 初始化 / 删除软件 ======

    def on_reset_clicked(self):
        """
        “初始化(清空)”按钮：
        - 清空所有应用和别名
        - 清空嵌入和缓存
        """
        reply = QtWidgets.QMessageBox.question(
            self,
            "确认初始化",
            "这一步会清空所有已配置的应用和别名，无法恢复。\n\n确定要继续吗？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        # 1) 清空内存中的 app 列表
        self.store.apps = []
        # 2) 保存到配置文件
        self.store.save()

        # 3) 清空 matcher 中的向量和缓存
        self.matcher.alias_vectors = np.zeros((0, 1), dtype=np.float32)
        self.matcher.alias_meta = []
        if hasattr(self.matcher, "cache"):
            self.matcher.cache.cache.clear()
            self.matcher.cache.save()

        # 4) 刷新表格
        self._load_from_store()

        QtWidgets.QMessageBox.information(
            self,
            "完成",
            "已清空所有应用配置。\n你可以点击“扫描桌面”重新获取应用列表。",
        )

    def on_delete_clicked(self):
        """
        顶部“删除选中软件”按钮：
        - 可以一次删多行
        - 会更新配置文件和嵌入缓存
        """
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            QtWidgets.QMessageBox.information(self, "提示", "请先在列表中选中要删除的软件。")
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "确认删除",
            "将会删除选中的软件以及它的所有别名，确定继续吗？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        # 行号从大到小删，避免索引错乱
        rows = sorted([idx.row() for idx in selected], reverse=True)

        for row in rows:
            if hasattr(self.store, "delete_app"):
                self.store.delete_app(row)
            else:
                # 兼容：没有 delete_app 方法就直接 pop
                if 0 <= row < len(self.store.apps):
                    self.store.apps.pop(row)

        # 删除软件会改变 app_index，所以缓存里的 (index, alias) 都不可靠了
        if hasattr(self.matcher, "cache"):
            self.matcher.cache.cache.clear()
            self.matcher.cache.save()

        # 保存配置 & 重建嵌入
        self.store.save()
        self.matcher.rebuild()

        # 刷新表格
        self._load_from_store()

    # ====== 表格右键菜单（管理别名 / 删除软件） ======

    def on_table_context_menu(self, pos: QtCore.QPoint):
        """
        表格右键菜单：
        - 只在“名称”列右键生效
        - 提供：管理别名... / 删除此软件
        """
        index = self.table.indexAt(pos)
        if not index.isValid():
            return

        row = index.row()
        col = index.column()
        if col != 0:
            return  # 只在第一列（名称列）弹菜单

        menu = QtWidgets.QMenu(self)
        act_alias = menu.addAction("管理别名...")
        act_delete = menu.addAction("删除此软件")  # 新增

        action = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if action == act_alias:
            dlg = AliasManagerDialog(self.store, row, self)
            if dlg.exec_() == QtWidgets.QDialog.Accepted:
                # 别名有变化，保存并重建嵌入
                self.store.save()
                self.matcher.rebuild()
                self._load_from_store()
        elif action == act_delete:
            # 复用上面删除逻辑，但只删一行
            reply = QtWidgets.QMessageBox.question(
                self,
                "确认删除",
                "将会删除该软件以及它的所有别名，确定继续吗？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

            if hasattr(self.store, "delete_app"):
                self.store.delete_app(row)
            else:
                if 0 <= row < len(self.store.apps):
                    self.store.apps.pop(row)

            if hasattr(self.matcher, "cache"):
                self.matcher.cache.cache.clear()
                self.matcher.cache.save()

            self.store.save()
            self.matcher.rebuild()
            self._load_from_store()

    # ====== 加载 / 扫描 / 表格基础逻辑 ======

    def _load_from_store(self):
        """从 store.apps 加载数据到表格"""
        self._updating_table = True

        apps = self.store.apps
        self.table.setRowCount(len(apps))

        for row, app in enumerate(apps):
            aliases = app.get("aliases", [])
            display_name = aliases[0] if aliases else app.get("base_name", app.get("id", ""))
            exe_path = app.get("exe_path", "")

            item_name = QtWidgets.QTableWidgetItem(display_name)
            item_path = QtWidgets.QTableWidgetItem(exe_path)

            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, item_path)

        self._updating_table = False

    def _scan_desktop_auto(self):
        """对话框初始化时自动扫描一次桌面（追加新应用）"""
        self._add_desktop_candidates(auto_save=True)

    def _add_desktop_candidates(self, auto_save: bool):
        """
        扫描桌面，把新路径追加到 store.apps：
        - 不动原来已经存在的软件和别名
        - 只根据 exe_path 去重
        - auto_save=True 时：立即保存配置并重建嵌入（你要的“点完就生效”）
        """
        existing_paths = {app.get("exe_path") for app in self.store.apps}

        candidates = scan_desktop_executables()
        if not candidates:
            return

        self._updating_table = True

        added = False
        for name, path in candidates:
            if path in existing_paths:
                continue  # 已存在的不动，别名也不改
            app_id = name.replace(" ", "_")
            self.store.add_app(app_id, path, name)
            existing_paths.add(path)
            added = True

        if added and auto_save:
            # 立刻保存配置并重建嵌入 → 不用再手动点“保存”
            self.store.save()
            self.matcher.rebuild()

        self._load_from_store()
        self._updating_table = False

    def on_add_clicked(self):
        """
        手动添加一条记录：
        - 先选择添加类型（文件 / 文件夹）
        - 选择路径
        - 默认用文件 / 文件夹名作为显示名称（用户可修改）
        """
        # 1) 先选添加类型
        add_type, ok = QtWidgets.QInputDialog.getItem(
            self,
            "选择添加类型",
            "请选择要添加的类型：",
            ["文件", "文件夹"],
            0,
            False
        )
        if not ok:
            return

        # 2) 根据类型选择路径
        if add_type == "文件":
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "选择要打开的文件或程序",
                "",
                "所有文件 (*.*)",
            )
        else:
            path = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                "选择要打开的文件夹",
                "",
                QtWidgets.QFileDialog.ShowDirsOnly
            )

        if not path:
            return  # 没选就算了

        # 3) 从路径里抽出一个默认名称
        #    - 文件夹：用文件夹名
        #    - 文件：默认用去掉扩展名的文件名（比如 xxx.exe -> xxx）
        base_name = os.path.basename(path.rstrip(r"\/"))
        if os.path.isfile(path):
            base_name = os.path.splitext(base_name)[0]

        # 4) 弹出输入框，让用户确认 / 修改显示名称
        text, ok = QtWidgets.QInputDialog.getText(
            self,
            "自定义名字",
            "请输入显示名称：",
            text=base_name  # ★ 默认填入文件/文件夹名
        )
        if not ok:
            return
        display_name = text.strip()
        if not display_name:
            return

        # 5) 写入配置并重建嵌入
        app_id = display_name.replace(" ", "_")
        exe_path = path  # 可能是文件，也可能是文件夹

        self.store.add_app(app_id, exe_path, display_name)
        self.store.save()
        self.matcher.rebuild()
        self._load_from_store()




    def on_scan_clicked(self):
        """点击“扫描桌面”按钮：再次扫描桌面并追加新应用"""
        # 这里 auto_save=True：扫描到新软件就立即写配置 + 重建嵌入
        self._add_desktop_candidates(auto_save=True)

    def on_item_changed(self, item: QtWidgets.QTableWidgetItem):
        """用户修改了表格中的名称或路径"""
        if self._updating_table:
            return

        row = item.row()
        name_item = self.table.item(row, 0)
        path_item = self.table.item(row, 1)
        if name_item is None or path_item is None:
            return

        display_name = name_item.text().strip()
        exe_path = path_item.text().strip()
        self.store.update_app(row, display_name, exe_path)

    def on_save(self):
        """
        点击“保存”按钮：
        - 把当前 store.apps 写回 apps_config.json
        - 调 matcher.rebuild() 重建所有别名的嵌入
        （手动添加 / 扫描已经自动保存了，这里主要是双击编辑名称/路径这种情况）
        """
        self.store.save()
        self.matcher.rebuild()
        self.accept()

