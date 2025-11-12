# app_launcher/gui/settings_dialog.py
# -*- coding: utf-8 -*-

from PyQt5 import QtWidgets, QtCore


class SettingsDialog(QtWidgets.QDialog):
    """用于设置“是否显示悬浮窗”的对话框"""

    def __init__(self, parent=None, show_floating: bool = True):
        """
        构造函数
        :param parent: 父窗口
        :param show_floating: 当前悬浮窗是否显示，用来初始化复选框
        """
        super().__init__(parent)  # 调用父类构造函数

        self.setWindowTitle("设置")  # 设置窗口标题
        self.resize(260, 140)  # 设置默认大小

        # 设置窗口标志：普通窗口，带最小化/最大化/关闭按钮
        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.WindowMinimizeButtonHint
            | QtCore.Qt.WindowMaximizeButtonHint
            | QtCore.Qt.WindowCloseButtonHint
        )

        # 创建一个复选框控件
        self.checkbox = QtWidgets.QCheckBox("显示悬浮窗")  # 显示文字
        self.checkbox.setChecked(show_floating)  # 设置初始状态

        # 创建一个按钮盒，包含“确定”和“取消”
        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )

        # 创建垂直布局，作为对话框的根布局
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.checkbox)  # 把复选框添加进布局
        layout.addStretch()  # 添加弹性空间
        layout.addWidget(btn_box)  # 把按钮盒添加进布局

        # 连接按钮盒的信号：确定 -> accept，取消 -> reject
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

    def get_result(self) -> bool:
        """返回复选框当前是否勾选"""
        return self.checkbox.isChecked()
