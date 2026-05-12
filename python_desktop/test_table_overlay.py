from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from overlay import TestTableOverlayWindow


def main() -> int:
    app = QApplication(sys.argv)
    overlay = TestTableOverlayWindow()
    overlay.show_table()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
