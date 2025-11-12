# app_launcher/gui/tray.py
# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets, QtGui, QtCore
import os
from app_launcher.utils.resources import resource_path


class AppTrayIcon(QtWidgets.QSystemTrayIcon):
    show_window = QtCore.pyqtSignal()
    hide_window = QtCore.pyqtSignal()
    open_settings = QtCore.pyqtSignal()
    open_app_config = QtCore.pyqtSignal()
    open_query = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # 1. 设置图标
        icon_path = resource_path("img/app_icon.ico")
        if os.path.exists(icon_path):
            icon = QtGui.QIcon(icon_path)
        else:
            icon = QtWidgets.QApplication.windowIcon()
            if icon.isNull():
                app_style = QtWidgets.QApplication.style()
                icon = app_style.standardIcon(QtWidgets.QStyle.SP_ComputerIcon)
        self.setIcon(icon)

        # 2. ★ 设置悬停提示文本（这里写你想显示的说明）
        self.setToolTip("RocketDesk：桌面应用搜索与快速启动工具")

        # 3. 创建右键菜单
        self._create_menu()

        # 4. 连接点击信号
        self.activated.connect(self.on_activated)

    def _create_menu(self):
        menu = QtWidgets.QMenu()
        act_show = menu.addAction("显示悬浮窗")
        act_hide = menu.addAction("隐藏悬浮窗")
        act_settings = menu.addAction("设置...")
        act_app_cfg = menu.addAction("设置启动 App...")
        act_query = menu.addAction("查询...")
        menu.addSeparator()
        act_exit = menu.addAction("退出")

        act_show.triggered.connect(self.show_window)
        act_hide.triggered.connect(self.hide_window)
        act_settings.triggered.connect(self.open_settings)
        act_app_cfg.triggered.connect(self.open_app_config)
        act_query.triggered.connect(self.open_query)
        act_exit.triggered.connect(QtWidgets.qApp.quit)

        self.setContextMenu(menu)

    def on_activated(self, reason: QtWidgets.QSystemTrayIcon.ActivationReason):
        if reason == QtWidgets.QSystemTrayIcon.DoubleClick:
            self.show_window.emit()
