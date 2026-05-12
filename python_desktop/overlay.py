from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget


class OverlayWindow(QWidget):
    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.avatar = QLabel("??")
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar.setFixedSize(112, 112)
        self.avatar.setStyleSheet(
            """
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #60A5FA, stop:1 #A78BFA);
                color: white;
                border-radius: 56px;
                font-size: 36px;
                font-weight: 900;
            }
            """
        )

        self.name = QLabel("")
        self.name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name.setFont(QFont("Sans Serif", 14, QFont.Weight.Bold))
        self.name.setStyleSheet("color: white; background: rgba(15, 23, 42, 210); border-radius: 12px; padding: 8px 12px;")

        self.status = QLabel("в сети")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("color: #BBF7D0; background: rgba(15, 23, 42, 210); border-radius: 12px; padding: 5px 12px;")

        layout = QVBoxLayout(self)
        layout.addWidget(self.avatar, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.name)
        layout.addWidget(self.status)

        self.setFixedSize(240, 230)

    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(15, 23, 42, 160))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect().adjusted(4, 4, -4, -4), 28, 28)
        super().paintEvent(event)

    def show_member(self, name: str, status: str = "в сети", duration_ms: int = 5000) -> None:
        self.avatar.setText(_initials(name))
        self.name.setText(name)
        self.status.setText(status)
        self.move(40, 40)
        self.show()
        self.raise_()
        QTimer.singleShot(duration_ms, self.hide)


class RoomStatusOverlayWindow(QWidget):
    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.dot = QLabel()
        self.dot.setFixedSize(14, 14)

        self.title = QLabel("Комната")
        self.title.setStyleSheet("color: #CBD5E1; font-size: 11px; font-weight: 900; letter-spacing: 1px;")

        self.room = QLabel("Комната")
        self.room.setFont(QFont("Sans Serif", 15, QFont.Weight.Bold))
        self.room.setStyleSheet("color: #F8FAFC;")

        self.status = QLabel("Не подключено")
        self.status.setStyleSheet("color: #BFDBFE;")

        self.event_label = QLabel("")
        self.event_label.setWordWrap(True)
        self.event_label.setStyleSheet("color: #CBD5E1; border-top: 1px solid rgba(148, 163, 184, 70); padding-top: 8px;")

        text = QVBoxLayout()
        text.setSpacing(3)
        text.addWidget(self.title)
        text.addWidget(self.room)
        text.addWidget(self.status)

        header = QHBoxLayout()
        header.setSpacing(12)
        header.addWidget(self.dot, alignment=Qt.AlignmentFlag.AlignTop)
        header.addLayout(text, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        layout.addLayout(header)
        layout.addWidget(self.event_label)

        self.setFixedSize(320, 150)
        self.update_room("Комната", "Не подключено", False)

    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(15, 23, 42, 210))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect().adjusted(4, 4, -4, -4), 24, 24)
        super().paintEvent(event)

    def update_room(self, room: str, status: str, online: bool, last_event: str = "") -> None:
        self.room.setText(room or "Комната")
        self.status.setText(status)
        self.event_label.setText(last_event)
        self.event_label.setVisible(bool(last_event))
        color = "#22C55E" if online else "#94A3B8"
        self.dot.setStyleSheet(f"background: {color}; border-radius: 7px;")

    def show_status(self) -> None:
        self.move(40, 280)
        self.show()
        self.raise_()


def _initials(name: str) -> str:
    letters = [part[0] for part in name.split() if part]
    return "".join(letters[:2]).upper() or "??"
