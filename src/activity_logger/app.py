"""Application bootstrap: QApplication, DB setup, logging, excepthook."""

from __future__ import annotations

import logging
import logging.handlers
import sys
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox

from activity_logger import config


def _setup_logging() -> None:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        config.LOG_DIR / "app.log", maxBytes=1_000_000, backupCount=3
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[handler, logging.StreamHandler()],
    )


def _apply_theme(app: QApplication, theme: str) -> None:
    if theme not in ("light", "dark"):
        return
    app.setStyle("Fusion")
    if theme == "dark":
        from PySide6.QtGui import QColor, QPalette
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor(53, 53, 53))
        pal.setColor(QPalette.WindowText, QColor(255, 255, 255))
        pal.setColor(QPalette.Base, QColor(35, 35, 35))
        pal.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        pal.setColor(QPalette.ToolTipBase, QColor(0, 0, 0))
        pal.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
        pal.setColor(QPalette.Text, QColor(255, 255, 255))
        pal.setColor(QPalette.Button, QColor(53, 53, 53))
        pal.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        pal.setColor(QPalette.BrightText, QColor(255, 0, 0))
        pal.setColor(QPalette.Link, QColor(42, 130, 218))
        pal.setColor(QPalette.Highlight, QColor(42, 130, 218))
        pal.setColor(QPalette.HighlightedText, QColor(35, 35, 35))
        app.setPalette(pal)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Activity Logger")
    app.setOrganizationName("Federal Activity Logger")

    def _excepthook(exc_type, exc_val, exc_tb) -> None:
        msg = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
        logging.critical("Unhandled exception:\n%s", msg)
        QMessageBox.critical(
            None,
            "Unexpected Error",
            f"An unexpected error occurred.\n\nLog: {config.LOG_DIR / 'app.log'}\n\n{msg[:600]}",
        )

    sys.excepthook = _excepthook

    try:
        _setup_logging()
    except Exception:
        pass  # logging failure must not kill the app

    from activity_logger.db import connection, migrations, seed

    try:
        conn = connection.connect()
        migrations.migrate(conn)
        seed.seed(conn)
    except RuntimeError as e:
        QMessageBox.critical(None, "Cannot Open Database", str(e))
        sys.exit(1)

    cfg = config.load()
    _apply_theme(app, cfg.get("theme", "system"))

    from activity_logger.ui.main_window import MainWindow

    window = MainWindow(conn, cfg)
    window.show()
    sys.exit(app.exec())
