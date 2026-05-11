from __future__ import annotations

import sys
from typing import Any

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

import api
from autostart import enable_autostart
from config import APP_NAME, HEARTBEAT_INTERVAL_SECONDS
from overlay import OverlayWindow
from realtime import RealtimeClient
from storage import AppState, clear_session, load_state, save_state


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.state = load_state()
        self.realtime: RealtimeClient | None = None
        self.overlay = OverlayWindow()

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(720, 520)

        self.status_label = QLabel("Не подключено")
        self.name_input = QLineEdit(self.state.name)
        self.invite_input = QLineEdit(self.state.invite_code)
        self.room_label = QLabel("")
        self.events_label = QLabel("Пока нет событий от других участников.")

        self.form_widget = QWidget()
        self.session_widget = QWidget()
        self.heartbeat_timer = QTimer(self)
        self.heartbeat_timer.timeout.connect(self.send_heartbeat)

        self.setup_ui()
        self.setup_tray()
        self.render_state()

        if self.state.has_session:
            self.start_presence()

    def setup_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        title = QLabel("Совместная работа за ноутом")
        title.setStyleSheet("font-size: 26px; font-weight: 800;")
        layout.addWidget(title)
        layout.addWidget(self.status_label)

        form_layout = QGridLayout(self.form_widget)
        form_layout.addWidget(self.room_box("Войти", "Подключиться к уже созданной комнате.", self.join_room), 0, 0)
        form_layout.addWidget(self.room_box("Создать комнату", "Придумай invite code и передай его другому человеку.", self.create_room), 0, 1)
        layout.addWidget(self.form_widget)

        session_layout = QVBoxLayout(self.session_widget)
        session_layout.addWidget(self.room_label)
        reset_button = QPushButton("Сбросить сессию")
        reset_button.clicked.connect(self.reset_session)
        autostart_button = QPushButton("Включить автозапуск")
        autostart_button.clicked.connect(self.enable_autostart)
        row = QHBoxLayout()
        row.addWidget(reset_button)
        row.addWidget(autostart_button)
        session_layout.addLayout(row)
        layout.addWidget(self.session_widget)

        events_title = QLabel("Последние события")
        events_title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(events_title)
        layout.addWidget(self.events_label)
        layout.addStretch(1)

        self.setCentralWidget(root)

    def room_box(self, title: str, description: str, action: Any) -> QGroupBox:
        box = QGroupBox(title)
        layout = QVBoxLayout(box)
        description_label = QLabel(description)
        description_label.setWordWrap(True)
        layout.addWidget(description_label)

        name = QLineEdit()
        name.setPlaceholderText("Имя")
        name.setText(self.state.name)
        name.textChanged.connect(lambda value: self.update_text("name", value))
        layout.addWidget(name)

        invite = QLineEdit()
        invite.setPlaceholderText("Invite code")
        invite.setText(self.state.invite_code)
        invite.textChanged.connect(lambda value: self.update_text("invite_code", value))
        layout.addWidget(invite)

        button = QPushButton(title)
        button.clicked.connect(action)
        layout.addWidget(button)

        return box

    def setup_tray(self) -> None:
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(make_icon())
        self.tray.setToolTip(APP_NAME)

        menu = QMenu()
        open_action = QAction("Открыть", self)
        open_action.triggered.connect(self.show_normal)
        hide_action = QAction("Скрыть", self)
        hide_action.triggered.connect(self.hide)
        quit_action = QAction("Выйти", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(open_action)
        menu.addAction(hide_action)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.show()

    def update_text(self, field: str, value: str) -> None:
        setattr(self.state, field, value)
        save_state(self.state)

    def join_room(self) -> None:
        self.submit(api.join_room, "Вы вошли в комнату")

    def create_room(self) -> None:
        self.submit(api.create_room, "Комната создана")

    def submit(self, action: Any, success_message: str) -> None:
        if not self.state.name or not self.state.invite_code:
            QMessageBox.warning(self, APP_NAME, "Заполни имя и invite code.")
            return

        try:
            payload = action(self.state)
            api.apply_join_response(self.state, payload)
            save_state(self.state)
            self.status_label.setText(success_message)
            self.render_state()
            self.start_presence()
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))

    def render_state(self) -> None:
        self.form_widget.setVisible(not self.state.has_session)
        self.session_widget.setVisible(self.state.has_session)

        if self.state.has_session:
            self.room_label.setText(f"Вы в комнате: {self.state.team_name}")

    def start_presence(self) -> None:
        self.stop_presence()
        self.send_heartbeat()
        self.heartbeat_timer.start(HEARTBEAT_INTERVAL_SECONDS * 1000)
        self.realtime = RealtimeClient(self.state)
        self.realtime.status_changed.connect(self.status_label.setText)
        self.realtime.event_received.connect(self.handle_presence_event)
        self.realtime.start()

    def stop_presence(self) -> None:
        self.heartbeat_timer.stop()

        if self.realtime:
            self.realtime.stop()
            self.realtime = None

    def send_heartbeat(self) -> None:
        try:
            api.heartbeat(self.state)
        except Exception as exc:
            self.status_label.setText(f"Heartbeat ошибка: {exc}")

    def handle_presence_event(self, payload: dict[str, Any]) -> None:
        event_type = payload.get("type")
        user = payload.get("user", {})
        device = payload.get("device", {})
        name = user.get("name") or "Участник"

        if event_type == "member_online":
            self.events_label.setText(f"{name} в сети ({device.get('name') or 'устройство'})")
            self.tray.showMessage(APP_NAME, f"{name} в сети", QSystemTrayIcon.MessageIcon.Information, 4000)
            self.overlay.show_member(name)
        elif event_type == "member_offline":
            self.events_label.setText(f"{name} вышел из сети")

    def reset_session(self) -> None:
        self.stop_presence()
        clear_session(self.state)
        self.status_label.setText("Не подключено")
        self.events_label.setText("Пока нет событий от других участников.")
        self.render_state()

    def enable_autostart(self) -> None:
        try:
            enable_autostart(APP_NAME)
            QMessageBox.information(self, APP_NAME, "Автозапуск включен.")
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))

    def show_normal(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: Any) -> None:
        event.ignore()
        self.hide()


def make_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#60A5FA"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(8, 8, 48, 48)
    painter.end()

    return QIcon(pixmap)


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
