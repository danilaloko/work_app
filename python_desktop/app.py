from __future__ import annotations

import sys
from typing import Any

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

import api
from autostart import enable_autostart
from config import APP_NAME, HEARTBEAT_INTERVAL_SECONDS
from overlay import OverlayWindow, RoomStatusOverlayWindow
from realtime import RealtimeClient
from storage import AppState, clear_session, load_state, save_state

AVATAR_PRESETS = {
    "cat": "Кот",
    "dog": "Пёс",
    "fox": "Лис",
    "robot": "Робот",
}

ITEM_PRESETS = {
    "coffee": "Кофе",
    "laptop": "Ноутбук",
    "book": "Книга",
    "plant": "Растение",
}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.state = load_state()
        self.realtime: RealtimeClient | None = None
        self.overlay = OverlayWindow()
        self.room_overlay = RoomStatusOverlayWindow()
        self.room_overlay_last_event = ""
        self.status_online = False

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(860, 620)

        self.status_label = QLabel("Не подключено")
        self.status_label.setObjectName("statusBadge")
        self.name_input = QLineEdit(self.state.name)
        self.invite_input = QLineEdit(self.state.invite_code)
        self.room_label = QLabel("")
        self.events_label = QLabel("Пока нет событий от других участников.")
        self.events_label.setObjectName("eventCard")
        self.room_overlay_checkbox = QCheckBox("Постоянный оверлей комнаты")
        self.room_overlay_checkbox.setChecked(self.state.room_overlay_always_on)
        self.room_overlay_checkbox.toggled.connect(self.toggle_room_overlay)
        self.avatar_select = QComboBox()
        self.item_select = QComboBox()

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
        root.setObjectName("root")
        root.setMinimumWidth(820)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(18)

        header = QFrame()
        header.setObjectName("hero")
        header.setMinimumHeight(126)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 22, 24, 22)

        copy = QVBoxLayout()
        eyebrow = QLabel("PRESENCE DESKTOP")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("Совместная работа за ноутом")
        title.setObjectName("title")
        subtitle = QLabel("Уведомления и аватары поверх экрана, когда участник появляется онлайн.")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        copy.addWidget(eyebrow)
        copy.addWidget(title)
        copy.addWidget(subtitle)
        header_layout.addLayout(copy, 1)
        header_layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(header)

        form_layout = QGridLayout(self.form_widget)
        form_layout.setSpacing(16)
        form_layout.addWidget(self.room_box("Войти", "Подключиться к уже созданной комнате.", self.join_room), 0, 0)
        form_layout.addWidget(self.room_box("Создать комнату", "Придумай invite code и передай его другому человеку.", self.create_room), 0, 1)
        self.form_widget.setMinimumHeight(178)
        layout.addWidget(self.form_widget)

        session_layout = QVBoxLayout(self.session_widget)
        session_layout.setContentsMargins(0, 0, 0, 0)
        self.room_label.setObjectName("sessionCard")
        session_layout.addWidget(self.room_label)
        reset_button = QPushButton("Сбросить сессию")
        reset_button.setProperty("variant", "secondary")
        reset_button.clicked.connect(self.reset_session)
        autostart_button = QPushButton("Включить автозапуск")
        autostart_button.setProperty("variant", "secondary")
        autostart_button.clicked.connect(self.enable_autostart)
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(reset_button)
        row.addWidget(autostart_button)
        session_layout.addLayout(row)
        layout.addWidget(self.session_widget)

        settings = QGroupBox("Настройки")
        settings.setObjectName("settingsCard")
        settings.setMinimumHeight(196)
        settings_layout = QVBoxLayout(settings)
        settings_layout.setContentsMargins(18, 34, 18, 18)
        settings_layout.setSpacing(8)
        settings_layout.addWidget(self.room_overlay_checkbox)
        settings_hint = QLabel("Показывает статус комнаты поверх окон. Входы и выходы участников всё равно всплывают отдельно.")
        settings_hint.setObjectName("description")
        settings_hint.setWordWrap(True)
        settings_layout.addWidget(settings_hint)
        settings_layout.addWidget(self.preset_selector("Аватар", self.avatar_select, AVATAR_PRESETS, self.state.avatar_key, self.update_avatar_key))
        settings_layout.addWidget(self.preset_selector("Предмет", self.item_select, ITEM_PRESETS, self.state.item_key, self.update_item_key))
        layout.addWidget(settings)

        events_title = QLabel("Последние события")
        events_title.setObjectName("sectionTitle")
        layout.addWidget(events_title)
        layout.addWidget(self.events_label)
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setObjectName("mainScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(root)
        self.setCentralWidget(scroll)

    def room_box(self, title: str, description: str, action: Any) -> QGroupBox:
        box = QGroupBox(title)
        box.setObjectName("roomCard")
        box.setMinimumHeight(166)
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(22, 34, 22, 22)
        layout.setSpacing(14)
        description_label = QLabel(description)
        description_label.setObjectName("description")
        description_label.setWordWrap(True)
        layout.addWidget(description_label)

        name = QLineEdit()
        name.setPlaceholderText("Имя")
        name.setText(self.state.name)
        name.setMinimumHeight(40)
        name.textChanged.connect(lambda value: self.update_text("name", value))
        layout.addWidget(name)

        invite = QLineEdit()
        invite.setPlaceholderText("Invite code")
        invite.setText(self.state.invite_code)
        invite.setMinimumHeight(40)
        invite.textChanged.connect(lambda value: self.update_text("invite_code", value))
        layout.addWidget(invite)

        button = QPushButton(title)
        button.setMinimumHeight(42)
        button.clicked.connect(action)
        layout.addWidget(button)

        return box

    def preset_selector(
        self,
        title: str,
        select: QComboBox,
        presets: dict[str, str],
        current: str,
        action: Any,
    ) -> QWidget:
        widget = QWidget()
        widget.setMinimumHeight(68)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel(title)
        label.setObjectName("description")
        layout.addWidget(label)

        for key, label_text in presets.items():
            select.addItem(label_text, key)

        index = select.findData(current)
        select.setCurrentIndex(index if index >= 0 else 0)
        select.setMinimumHeight(38)
        select.currentIndexChanged.connect(lambda _: action(select.currentData()))
        layout.addWidget(select)

        return widget

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

    def update_avatar_key(self, value: str) -> None:
        self.state.avatar_key = value or "cat"
        save_state(self.state)

    def update_item_key(self, value: str) -> None:
        self.state.item_key = value or "coffee"
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
            self.set_status(success_message, online=True)
            self.render_state()
            self.start_presence()
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, str(exc))

    def render_state(self) -> None:
        self.form_widget.setVisible(not self.state.has_session)
        self.session_widget.setVisible(self.state.has_session)

        if self.state.has_session:
            self.room_label.setText(f"Вы в комнате: {self.state.team_name}\nHeartbeat отправляется каждые 25 секунд.")
        self.update_room_overlay()

    def start_presence(self) -> None:
        self.stop_presence()
        self.send_heartbeat()
        self.heartbeat_timer.start(HEARTBEAT_INTERVAL_SECONDS * 1000)
        self.realtime = RealtimeClient(self.state)
        self.realtime.status_changed.connect(self.set_status)
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
            self.set_status(f"Heartbeat ошибка: {exc}", online=False)

    def handle_presence_event(self, payload: dict[str, Any]) -> None:
        event_type = payload.get("type")
        user = payload.get("user", {})
        device = payload.get("device", {})
        name = user.get("name") or "Участник"
        device_name = device.get("name") or "устройство"

        if event_type == "member_online":
            self.room_overlay_last_event = f"{name} в сети · {device_name}"
            self.events_label.setText(f"{name} в сети ({device_name})")
            self.tray.showMessage(APP_NAME, f"{name} в сети", QSystemTrayIcon.MessageIcon.Information, 4000)
            self.overlay.show_member(name, "в сети")
        elif event_type == "member_offline":
            self.room_overlay_last_event = f"{name} вышел · {device_name}"
            self.events_label.setText(f"{name} вышел из сети")
            self.tray.showMessage(APP_NAME, f"{name} вышел из сети", QSystemTrayIcon.MessageIcon.Information, 4000)
            self.overlay.show_member(name, "вышел из сети")

        self.update_room_overlay()

    def reset_session(self) -> None:
        self.stop_presence()
        self.room_overlay.hide()
        self.room_overlay_last_event = ""
        clear_session(self.state)
        self.set_status("Не подключено", online=False)
        self.events_label.setText("Пока нет событий от других участников.")
        self.render_state()

    def set_status(self, text: str, online: bool | None = None) -> None:
        if online is None:
            online = "подключ" in text.lower() or "realtime подключен" in text.lower()

        self.status_label.setText(text)
        self.status_online = online
        self.status_label.setProperty("online", online)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.update_room_overlay()

    def toggle_room_overlay(self, enabled: bool) -> None:
        self.state.room_overlay_always_on = enabled
        save_state(self.state)
        self.update_room_overlay()

    def update_room_overlay(self) -> None:
        if not self.state.room_overlay_always_on or not self.state.has_session:
            self.room_overlay.hide()
            return

        self.room_overlay.update_room(
            self.state.team_name or "Комната",
            self.status_label.text(),
            self.status_online,
            self.room_overlay_last_event,
        )
        self.room_overlay.show_status()

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


def app_stylesheet() -> str:
    return """
    QWidget#root {
        background: #0F172A;
        color: #E5E7EB;
        font-family: Inter, "Segoe UI", Arial, sans-serif;
        font-size: 14px;
    }

    QScrollArea#mainScroll {
        background: #0F172A;
        border: 0;
    }

    QScrollArea#mainScroll > QWidget > QWidget {
        background: #0F172A;
    }

    QFrame#hero, QGroupBox#roomCard, QLabel#sessionCard, QLabel#eventCard {
        background: rgba(30, 41, 59, 0.92);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 22px;
    }

    QLabel#eyebrow {
        color: #93C5FD;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 1.2px;
    }

    QLabel#title {
        color: #F8FAFC;
        font-size: 30px;
        font-weight: 900;
    }

    QLabel#subtitle, QLabel#description {
        color: #AAB6C7;
        font-size: 14px;
    }

    QLabel#sectionTitle {
        color: #F8FAFC;
        font-size: 19px;
        font-weight: 800;
        margin-top: 8px;
    }

    QGroupBox#settingsCard {
        color: #F8FAFC;
        background: rgba(30, 41, 59, 0.62);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 18px;
        font-size: 18px;
        font-weight: 900;
        padding-top: 14px;
    }

    QCheckBox {
        color: #E2E8F0;
        font-weight: 800;
        spacing: 10px;
    }

    QCheckBox::indicator {
        width: 18px;
        height: 18px;
    }

    QLabel#statusBadge {
        color: #CBD5E1;
        background: rgba(148, 163, 184, 0.18);
        border-radius: 15px;
        padding: 8px 14px;
        font-weight: 700;
    }

    QLabel#statusBadge[online="true"] {
        color: #BBF7D0;
        background: rgba(34, 197, 94, 0.18);
    }

    QLabel#sessionCard, QLabel#eventCard {
        padding: 18px;
        color: #DBEAFE;
        font-weight: 700;
    }

    QGroupBox#roomCard {
        color: #F8FAFC;
        font-size: 18px;
        font-weight: 900;
        padding-top: 14px;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        top: 8px;
        left: 20px;
        padding: 0 8px;
        background: transparent;
    }

    QLineEdit {
        min-height: 40px;
        color: #F8FAFC;
        background: #111827;
        border: 1px solid rgba(148, 163, 184, 0.28);
        border-radius: 12px;
        padding: 0 12px;
        selection-background-color: #60A5FA;
    }

    QLineEdit:focus {
        border: 1px solid #60A5FA;
        background: #0B1120;
    }

    QComboBox {
        min-height: 38px;
        color: #F8FAFC;
        background: #111827;
        border: 1px solid rgba(148, 163, 184, 0.28);
        border-radius: 12px;
        padding: 0 12px;
    }

    QPushButton {
        color: #0F172A;
        background: #93C5FD;
        border: 0;
        border-radius: 12px;
        padding: 10px 16px;
        font-weight: 900;
    }

    QPushButton:hover {
        background: #BFDBFE;
    }

    QPushButton:pressed {
        background: #60A5FA;
    }

    QPushButton[variant="secondary"] {
        color: #E2E8F0;
        background: rgba(148, 163, 184, 0.18);
    }

    QPushButton[variant="secondary"]:hover {
        background: rgba(148, 163, 184, 0.28);
    }

    QMenu {
        background: #111827;
        color: #F8FAFC;
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-radius: 10px;
        padding: 6px;
    }

    QMenu::item {
        padding: 8px 18px;
        border-radius: 8px;
    }

    QMenu::item:selected {
        background: #2563EB;
    }
    """


def apply_palette(app: QApplication) -> None:
    app.setStyleSheet(app_stylesheet())


def main() -> int:
    app = QApplication(sys.argv)
    apply_palette(app)
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
