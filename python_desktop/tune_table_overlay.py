from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from overlay import TABLE_LAYOUT, TestTableOverlayWindow

LAYOUT_PATH = Path(__file__).with_name("table_layout.json")
FIELDS = ("x", "y", "w", "h")
LABELS = {
    "table": "Стол",
    "left_avatar": "Левый кот",
    "right_avatar": "Правый кот",
    "left_item": "Левый предмет",
    "right_item": "Правый предмет",
}


class LayoutTuner(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.layout_config = self.load_layout()
        self.preview = TestTableOverlayWindow(self.layout_config)
        self.inputs: dict[str, list[QSpinBox]] = {}

        self.setWindowTitle("Table Overlay Tuner")
        self.setMinimumWidth(480)
        self.setup_ui()
        self.preview.show_table()

    def setup_ui(self) -> None:
        root = QVBoxLayout(self)
        hint = QLabel("Меняй координаты и размеры. Превью обновляется сразу. Save пишет table_layout.json.")
        hint.setWordWrap(True)
        root.addWidget(hint)

        for key, title in LABELS.items():
            group = QGroupBox(title)
            grid = QGridLayout(group)
            self.inputs[key] = []

            for column, field in enumerate(FIELDS):
                grid.addWidget(QLabel(field), 0, column)
                spin = QSpinBox()
                spin.setRange(-500, 1600)
                spin.setSingleStep(4)
                spin.setValue(self.layout_config[key][column])
                spin.valueChanged.connect(self.update_layout)
                grid.addWidget(spin, 1, column)
                self.inputs[key].append(spin)

            root.addWidget(group)

        save = QPushButton("Save layout")
        save.clicked.connect(self.save_layout)
        root.addWidget(save)

        reset = QPushButton("Reset defaults")
        reset.clicked.connect(self.reset_layout)
        root.addWidget(reset)
        root.addStretch(1)

    def update_layout(self) -> None:
        for key, inputs in self.inputs.items():
            self.layout_config[key] = [spin.value() for spin in inputs]

        self.preview.set_layout_config(self.layout_config)

    def save_layout(self) -> None:
        self.update_layout()
        LAYOUT_PATH.write_text(
            json.dumps(self.layout_config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(self.layout_config, ensure_ascii=False, indent=2), flush=True)

    def reset_layout(self) -> None:
        self.layout_config = deepcopy(TABLE_LAYOUT)

        for key, values in self.layout_config.items():
            for spin, value in zip(self.inputs[key], values):
                spin.blockSignals(True)
                spin.setValue(value)
                spin.blockSignals(False)

        self.preview.set_layout_config(self.layout_config)

    @staticmethod
    def load_layout() -> dict[str, list[int]]:
        if not LAYOUT_PATH.exists():
            return deepcopy(TABLE_LAYOUT)

        payload = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))

        return {
            key: [int(value) for value in payload.get(key, TABLE_LAYOUT[key])]
            for key in TABLE_LAYOUT
        }

    def closeEvent(self, event) -> None:  # noqa: ANN001
        self.preview.close()
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    tuner = LayoutTuner()
    tuner.show()
    tuner.raise_()
    tuner.activateWindow()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
