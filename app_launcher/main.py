# app_launcher/main.py
# -*- coding: utf-8 -*-

import sys  # 标准库：命令行参数、退出
from PyQt5 import QtWidgets, QtGui       # Qt 应用 & 图标
from PyQt5.QtNetwork import QLocalServer, QLocalSocket  # 单实例用本地服务器

from app_launcher.gui.floating_window import FloatingLauncher  # 悬浮窗主界面
from app_launcher.gui.tray import AppTrayIcon                  # 托盘图标
from app_launcher.utils.resources import resource_path         # 资源路径工具

# 单实例标识字符串（只要全局唯一就行）
SINGLE_INSTANCE_KEY = "RocketDesk_SingleInstance_Key_2025"


def is_already_running() -> bool:
    """
    判断是否已经有一个实例在运行。

    原理：
      - 用 QLocalSocket 尝试连接名为 SINGLE_INSTANCE_KEY 的本地服务器
      - 如果能连上，说明已有进程在 listen -> 返回 True
      - 否则返回 False
    """
    socket = QLocalSocket()
    socket.connectToServer(SINGLE_INSTANCE_KEY)
    # 等待一点时间看能不能连上
    if socket.waitForConnected(100):
        socket.close()
        return True
    # 没连上就断开
    socket.abort()
    return False


def create_single_instance_server(app: QtWidgets.QApplication) -> None:
    """
    创建一个本地服务器，占用 SINGLE_INSTANCE_KEY。
    只要这个 server 存在，后续进程就会被 is_already_running 检测到。
    """
    # 防止上次异常退出残留
    QLocalServer.removeServer(SINGLE_INSTANCE_KEY)

    server = QLocalServer(app)
    # 开始监听（失败就算了，不影响当前实例继续跑）
    server.listen(SINGLE_INSTANCE_KEY)

    # ★ 把 server 挂在 app 上，防止被垃圾回收
    app._single_instance_server = server


def main():
    # 先创建 Qt 应用对象
    app = QtWidgets.QApplication(sys.argv)

    # 全局应用图标
    icon_path = resource_path("img/app_icon.ico")
    app_icon = QtGui.QIcon(icon_path)
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    # ★ 这里先检查是否已有实例在运行
    if is_already_running():
        QtWidgets.QMessageBox.information(
            None,
            "RocketDesk",
            "RocketDesk 已经在运行中，不需要重复启动。",
        )
        return  # 直接退出 main()，不要再创建窗口和模型

    # ★ 当前是第一个实例：创建本地服务器，占住 SINGLE_INSTANCE_KEY
    create_single_instance_server(app)

    # 创建主悬浮窗
    win = FloatingLauncher()
    win.show()

    # 创建托盘图标（AppTrayIcon 内部已经设置好图标和菜单）
    tray = AppTrayIcon()
    tray.show()          # 没这句托盘不会显示
    app.tray = tray      # 保存引用，防止被 GC 回收

    # 关闭最后一个窗口时，不自动退出（托盘还在）
    app.setQuitOnLastWindowClosed(False)

    # 进入事件循环
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
