# app_launcher/gui/floating_window.py
# -*- coding: utf-8 -*-

"""
悬浮窗主界面：
- 无边框、可拖动、置顶
- 右键菜单：设置、设置启动App、查询、最小化到托盘、退出
- 支持托盘图标：右键托盘菜单 & 左键双击显示/隐藏
"""

import os  # 启动应用 / 文件
import sys  # 程序入口参数

from PyQt5 import QtWidgets, QtCore, QtGui

from app_launcher.core.config_store import AppConfigStore
from app_launcher.core.sentence_encoder import QwenSentenceEncoder
from app_launcher.core.matcher import AppMatcher
from app_launcher.core.alias_extractor import generate_alias

from app_launcher.gui.tray import AppTrayIcon
from app_launcher.gui.settings_dialog import SettingsDialog
from app_launcher.gui.app_config_dialog import AppConfigDialog
from app_launcher.gui.query_dialog import QueryDialog


class FloatingLauncher(QtWidgets.QWidget):
    """悬浮窗主窗口"""

    MAX_RESULTS = 3  # 搜索时最多输出几个候选

    def __init__(self, parent=None):
        """构造函数"""
        super().__init__(parent)

        # --- 核心数据对象 ---
        self.store = AppConfigStore()              # 配置存储
        self.encoder = QwenSentenceEncoder()       # 句向量编码器（此处建议先用轻量版本）
        self.matcher = AppMatcher(self.encoder, self.store)  # 匹配器

        # 悬浮窗是否逻辑上的“显示”状态
        self._show_floating = True

        # 用于拖动窗口时，记录点击位置
        self._drag_pos = None
        self._results_expanded = False  # 记录当前结果是否展开
        # 初始化界面控件
        self._init_ui()
        # 创建托盘图标
        #self._init_tray()
    """
    def _init_ui(self):
        #初始化悬浮窗界面
        self.setWindowTitle("Alias App Launcher")  # 标题（虽然无边框，但方便调试）

        # 固定初始大小
        self.setFixedSize(360, 90)

        # 无边框 + 置顶 + 工具窗口（不占任务栏）
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.Tool
        )

        # 根布局：垂直
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        # 第一行：输入框 + 搜索按钮
        h_layout = QtWidgets.QHBoxLayout()
        self.input_edit = QtWidgets.QLineEdit()
        self.input_edit.setPlaceholderText("例如：打开微信 / kakao 켜봐 / 열어줘 멜론")
        self.btn_search = QtWidgets.QPushButton("搜索")
        h_layout.addWidget(self.input_edit)
        h_layout.addWidget(self.btn_search)

        # 第二行：结果列表
        self.result_list = QtWidgets.QListWidget()
        self.result_list.setVisible(False)  # 没结果时隐藏

        main_layout.addLayout(h_layout)
        main_layout.addWidget(self.result_list)

        # 信号连接
        self.btn_search.clicked.connect(self.on_search_clicked)
        self.input_edit.returnPressed.connect(self.on_search_clicked)
        self.result_list.itemDoubleClicked.connect(self.on_result_double_clicked)

        # 启用自定义右键菜单
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)
    """
    def _init_ui(self):
        """初始化悬浮窗界面（紧贴卡片，没有多余外框）"""
        self.setWindowTitle("Alias App Launcher")

        # 无边框 + 置顶 + 工具窗口（不占任务栏）
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.Tool
        )

        # 允许透明背景，实现圆角卡片效果
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        # 根布局：整个窗口的布局
        root_layout = QtWidgets.QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 卡片容器：白底 + 圆角
        card = QtWidgets.QFrame()
        card.setObjectName("CardFrame")
        card.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.card = card   # ★ 记住这个，后面更新大小要用

        # 整个胶囊最小宽度
        card.setMinimumWidth(350)
        card.setStyleSheet("""
        QFrame#CardFrame {
            background-color: rgba(255, 255, 255, 245);
            border-radius: 12px;
            border: 1px solid rgba(0, 0, 0, 40);
        }
        QLineEdit {
            border-radius: 16px;
            border: 1px solid #cccccc;
            padding: 0 12px;
            background-color: #fdfdfd;
            selection-background-color: #0078d7;
            font-size: 12px;
        }
        QLineEdit:focus {
            border: 1px solid #0078d7;
            background-color: #ffffff;
        }
        QPushButton {
            border-radius: 16px;
            background-color: #0078d7;
            color: white;
            border: none;
            padding: 0 16px;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #1a88ff;
        }
        QPushButton:pressed {
            background-color: #005a9e;
        }
        QListWidget {
            border: none;
            background-color: transparent;
            font-size: 12px;
        }
        QToolButton {
            border: none;
            color: #666666;
            font-size: 11px;
            padding: 0 4px;
        }
        QToolButton:hover {
            color: #333333;
        }
        """)

        # 卡片内部布局
        card_layout = QtWidgets.QVBoxLayout(card)
        card_layout.setContentsMargins(10, 10, 10, 8)
        card_layout.setSpacing(6)

        # 第一行：搜索框 + 按钮
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)

        self.input_edit = QtWidgets.QLineEdit()
        self.input_edit.setPlaceholderText("例如：打开微信 / kakao 켜봐 / 멜론 열어줘")
        self.input_edit.setFixedHeight(32)
        self.input_edit.setMinimumWidth(300)

        self.btn_search = QtWidgets.QPushButton("搜索")
        self.btn_search.setFixedHeight(32)
        self.btn_search.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        top_layout.addWidget(self.input_edit)
        top_layout.addWidget(self.btn_search)

        # 第二行：结果列表
        self.result_list = QtWidgets.QListWidget()
        self.result_list.setVisible(False)    # 初始不显示
        self.result_list.setMinimumHeight(40)

        # 第三行：右下角一个减号按钮，用来收起结果区域
        toggle_layout = QtWidgets.QHBoxLayout()
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        toggle_layout.setSpacing(0)
        toggle_layout.addStretch()

        self.btn_close_results = QtWidgets.QToolButton()
        self.btn_close_results.setText("－")
        self.btn_close_results.setToolTip("收起搜索结果")
        self.btn_close_results.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.btn_close_results.setVisible(False)  # 没有结果时不显示
        toggle_layout.addWidget(self.btn_close_results)

        # 组装卡片
        card_layout.addLayout(top_layout)
        card_layout.addWidget(self.result_list)
        card_layout.addLayout(toggle_layout)

        # 卡片放到根布局
        root_layout.addWidget(card)

        # 只锁宽度，高度后面根据内容动态调
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self._update_size()

        # 信号连接
        self.btn_search.clicked.connect(self.on_search_clicked)
        self.input_edit.returnPressed.connect(self.on_search_clicked)
        self.result_list.itemDoubleClicked.connect(self.on_result_double_clicked)
        self.btn_close_results.clicked.connect(self.on_close_results)

        # 右键菜单
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)
    def _update_size(self):
        """根据当前可见内容更新窗口大小（只要你改了显示/隐藏就调一下）"""
        if not hasattr(self, "card") or self.card is None:
            return
        self.card.adjustSize()
        hint = self.card.sizeHint()
        # 窗口大小 = 卡片大小
        self.setFixedSize(hint.width(), hint.height())

    def _init_tray(self):
        """创建托盘图标并连接信号"""
        self.tray = AppTrayIcon(self)  # 创建托盘对象，父对象设为悬浮窗

        # 当托盘发出 show_window 时，调用 self.toggle_show_from_tray
        self.tray.show_window.connect(self.toggle_show_from_tray)
        # 托盘发出 hide_window 时，直接隐藏悬浮窗
        self.tray.hide_window.connect(self.hide_floating)
        # 托盘菜单里的“设置...” -> 打开设置对话框
        self.tray.open_settings.connect(self.open_settings_dialog)
        # “设置启动 App...” -> 打开配置对话框
        self.tray.open_app_config.connect(self.open_app_config_dialog)
        # “查询...” -> 打开查询对话框
        self.tray.open_query.connect(self.open_query_dialog)

        self.tray.show()  # 显示托盘图标

    # ---------------- GUI 基本行为（拖动 & 右键菜单） ----------------
    def mousePressEvent(self, event):
        """鼠标按下：记录拖动起始位置"""
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """鼠标移动：如果在拖动，则移动窗口"""
        if self._drag_pos is not None and event.buttons() & QtCore.Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放：结束拖动"""
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_pos = None
        super().mouseReleaseEvent(event)

    def on_context_menu(self, pos):
        """悬浮窗右键菜单"""
        menu = QtWidgets.QMenu(self)

        act_settings = menu.addAction("设置...")
        act_app_cfg = menu.addAction("设置启动 App...")
        act_query = menu.addAction("查询...")
        menu.addSeparator()
        act_minimize = menu.addAction("最小化到托盘")
        act_exit = menu.addAction("退出")

        action = menu.exec_(self.mapToGlobal(pos))

        if action == act_settings:
            self.open_settings_dialog()
        elif action == act_app_cfg:
            self.open_app_config_dialog()
        elif action == act_query:
            self.open_query_dialog()
        elif action == act_minimize:
            self.hide_floating()
        elif action == act_exit:
            QtWidgets.qApp.quit()

    # ---------------- 与托盘交互：显示 / 隐藏逻辑 ----------------
    def toggle_show_from_tray(self):
        """托盘双击时：如果当前隐藏就显示，否则隐藏"""
        if self.isVisible():
            self.hide_floating()
        else:
            self.show_floating()

    def show_floating(self):
        """显示悬浮窗"""
        self._show_floating = True
        self.show()
        self.raise_()   # 提到最前
        self.activateWindow()  # 激活窗口（获得焦点）

    def hide_floating(self):
        """隐藏悬浮窗（最小化到托盘）"""
        self._show_floating = False
        self.hide()

    def closeEvent(self, event):
        """
        拦截窗口关闭事件：
        用户点关闭（Alt+F4 / 任务栏右键关闭）时，不退出程序，只是隐藏到托盘
        """
        event.ignore()   # 阻止真正关闭
        self.hide_floating()  # 改为隐藏

    # ---------------- 右键菜单中的各个动作 ----------------
    def open_settings_dialog(self):
        """打开“设置”对话框"""
        dlg = SettingsDialog(self, show_floating=self._show_floating)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            should_show = dlg.get_result()
            if should_show:
                self.show_floating()
            else:
                self.hide_floating()

    def open_app_config_dialog(self):
        """打开“设置启动 App”对话框"""
        dlg = AppConfigDialog(self.store, self.matcher, self)
        dlg.exec_()

    def open_query_dialog(self):
        """打开“查询已配置应用”对话框"""
        dlg = QueryDialog(self.store, self)
        dlg.exec_()

    def on_search_clicked(self):
        """点击搜索按钮或回车键时执行"""
        text = self.input_edit.text().strip()
        if not text:
            QtWidgets.QMessageBox.information(self, "提示", "请输入指令，例如：打开微信 / kakao 켜봐")
            return

        # 1. 用别名模型抽取 App 名
        try:
            alias = generate_alias(text)
        except Exception as e:
            print("generate_alias error:", e)
            QtWidgets.QMessageBox.warning(self, "错误", f"别名模型调用失败：{e}")
            return

        alias = (alias or "").strip()
        if not alias:
            QtWidgets.QMessageBox.information(
                self, "提示", "未能从输入中抽取有效的 App 名称，请换个说法再试。"
            )
            return

        # 2. 调 matcher 做相似度搜索
        try:
            candidates = self.matcher.find_top_k(alias, k=3)
        except Exception as e:
            print("matcher.find_top_k error:", e)
            QtWidgets.QMessageBox.warning(self, "错误", f"应用匹配失败：{e}")
            return

        # 3. 渲染到列表
        self.result_list.clear()

        if not candidates:
            self.result_list.addItem("（没有匹配到已配置的应用，请先到“设置启动 App”中添加）")
        else:
            for c in candidates:
                base_name = c.get("base_name") or c.get("name") or "未知应用"
                match_alias = c.get("match_alias") or c.get("alias") or base_name
                exe_path = c.get("exe_path") or c.get("path") or ""
                score = c.get("score")
                if score is None:
                    score_text = ""
                else:
                    score_text = f" (score={float(score):.2f})"

                if match_alias == base_name:
                    alias_part = ""
                else:
                    alias_part = f"（匹配别名: {match_alias}）"

                text_show = f"{base_name}{alias_part}  →  {exe_path}{score_text}"
                item = QtWidgets.QListWidgetItem(text_show)
                item.setData(QtCore.Qt.UserRole, c)
                self.result_list.addItem(item)

        # 4. 显示结果区域和减号按钮
        self.result_list.setVisible(True)
        self.result_list.setMaximumHeight(16777215)  # 恢复正常高度
        self.btn_close_results.setVisible(True)

        # 5. 让窗口高度按内容更新
        self._update_size()




    def on_result_double_clicked(self, item: QtWidgets.QListWidgetItem):
        """双击列表某一项，打开对应路径"""
        data = item.data(QtCore.Qt.UserRole)
        if not isinstance(data, dict):
            return
        exe_path = data.get("exe_path")
        if not exe_path:
            return
        if not os.path.exists(exe_path):
            QtWidgets.QMessageBox.warning(self, "错误", f"路径不存在：\n{exe_path}")
            return
        try:
            os.startfile(exe_path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "启动失败", f"无法打开：\n{exe_path}\n\n错误信息：{e}"
            )

    def on_close_results(self):
        """点击减号：收起搜索结果区域并缩回窗口高度"""
        # 隐藏结果和减号，把结果列表高度也压到 0
        self.result_list.setVisible(False)
        self.result_list.setMaximumHeight(0)
        self.btn_close_results.setVisible(False)

        # 根据当前内容重新计算窗口大小（只剩一行搜索框）
        self._update_size()

# 单独运行本文件时的入口（调试用）
def main():
    app = QtWidgets.QApplication(sys.argv)
    win = FloatingLauncher()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
