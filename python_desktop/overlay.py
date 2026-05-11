from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont
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
                background: #60A5FA;
                color: white;
                border-radius: 56px;
                font-size: 34px;
                font-weight: 800;
            }
            """
        )

        self.name = QLabel("")
        self.name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name.setFont(QFont("Sans Serif", 14, QFont.Weight.Bold))
        self.name.setStyleSheet("color: white; background: rgba(15, 23, 42, 170); border-radius: 10px; padding: 6px;")

        self.status = QLabel("в сети")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("color: white; background: rgba(15, 23, 42, 170); border-radius: 10px; padding: 4px;")

        layout = QVBoxLayout(self)
        layout.addWidget(self.avatar, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.name)
        layout.addWidget(self.status)

        self.setFixedSize(220, 210)

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
