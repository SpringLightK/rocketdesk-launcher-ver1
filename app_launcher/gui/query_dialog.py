# app_launcher/gui/query_dialog.py
# -*- coding: utf-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QHeaderView

from app_launcher.core.config_store import AppConfigStore


class QueryDialog(QtWidgets.QDialog):
    """
    查询已配置应用：
    - 顶部：搜索框 + 查询按钮
    - 下方：表格显示名称和路径
    """

    def __init__(self, store: AppConfigStore, parent=None):
        """
        :param store: AppConfigStore 实例
        :param parent: 父窗口
        """
        super().__init__(parent)

        self.store = store  # 保存配置对象

        self.setWindowTitle("查询已配置应用")  # 设置窗口标题
        self.resize(800, 500)  # 默认大小

        # 普通可缩放窗口
        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.WindowMinimizeButtonHint
            | QtCore.Qt.WindowMaximizeButtonHint
            | QtCore.Qt.WindowCloseButtonHint
        )

        self._init_ui()  # 初始化界面

    def _init_ui(self):
        """初始化界面控件和布局"""
        main_layout = QtWidgets.QVBoxLayout(self)  # 根布局

        # 顶部：搜索框 + 按钮
        top_layout = QtWidgets.QHBoxLayout()
        self.search_edit = QtWidgets.QLineEdit()  # 输入关键字的编辑框
        self.search_edit.setPlaceholderText("输入名称或路径关键字进行过滤")
        self.btn_search = QtWidgets.QPushButton("查询")  # 查询按钮
        top_layout.addWidget(self.search_edit)
        top_layout.addWidget(self.btn_search)

        # 表格显示结果
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["应用名称", "可执行路径"])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 名称列自适应
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # 路径列拉伸

        # 把控件加到根布局
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.table)

        # 信号连接
        self.btn_search.clicked.connect(self.do_search)
        self.search_edit.returnPressed.connect(self.do_search)

        # 初次加载全部
        self._fill_table(self.store.apps)

    def _fill_table(self, apps):
        """用给定的 apps 列表填充表格"""
        self.table.setRowCount(len(apps))  # 设置表格行数
        for row, app in enumerate(apps):  # 遍历每条记录
            aliases = app.get("aliases", [])
            display_name = aliases[0] if aliases else app.get("id", "")
            exe_path = app.get("exe_path", "")

            item_name = QtWidgets.QTableWidgetItem(display_name)
            item_path = QtWidgets.QTableWidgetItem(exe_path)

            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, item_path)

    def do_search(self):
        """根据关键字过滤列表"""
        key = self.search_edit.text().strip().lower()  # 取关键字并转小写
        if not key:  # 关键字为空 -> 显示全部
            self._fill_table(self.store.apps)
            return

        filtered = []  # 存放过滤结果
        for app in self.store.apps:
            aliases = app.get("aliases", [])
            display_name = aliases[0] if aliases else app.get("id", "")
            exe_path = app.get("exe_path", "")

            if key in display_name.lower() or key in exe_path.lower():
                filtered.append(app)

        self._fill_table(filtered)  # 用过滤后的列表刷新表格
