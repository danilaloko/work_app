from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


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

    def show_member(self, name: str, duration_ms: int = 5000) -> None:
        self.avatar.setText(_initials(name))
        self.name.setText(name)
        self.move(40, 40)
        self.show()
        self.raise_()
        QTimer.singleShot(duration_ms, self.hide)


def _initials(name: str) -> str:
    letters = [part[0] for part in name.split() if part]
    return "".join(letters[:2]).upper() or "??"
