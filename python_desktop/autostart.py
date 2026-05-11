from __future__ import annotations

import os
import sys
from pathlib import Path


def enable_autostart(app_name: str = "Presence Desktop") -> None:
    if sys.platform.startswith("linux"):
        _enable_linux_autostart(app_name)
        return

    if sys.platform == "win32":
        _enable_windows_autostart(app_name)
        return

    raise RuntimeError("Автозапуск поддержан только для Linux и Windows")


def _enable_linux_autostart(app_name: str) -> None:
    autostart_dir = Path.home() / ".config" / "autostart"
    autostart_dir.mkdir(parents=True, exist_ok=True)
    desktop_file = autostart_dir / "presence-desktop.desktop"
    executable = Path(sys.argv[0]).resolve()

    desktop_file.write_text(
        "\n".join(
            [
                "[Desktop Entry]",
                "Type=Application",
                f"Name={app_name}",
                f"Exec={executable}",
                "Terminal=false",
                "X-GNOME-Autostart-enabled=true",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _enable_windows_autostart(app_name: str) -> None:
    startup = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup.mkdir(parents=True, exist_ok=True)
    cmd_file = startup / f"{app_name}.cmd"
    executable = Path(sys.argv[0]).resolve()

    cmd_file.write_text(f'start "" "{executable}"\n', encoding="utf-8")
