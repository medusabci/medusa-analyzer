from pathlib import Path

from PySide6.QtCore import QRect
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QProgressBar, QSplashScreen


class SplashScreen:
    """Runtime splash screen with startup progress feedback."""

    MAX_VALUE = 95
    IMAGE_NAME = "medusa_splash_v2026 copia.png"

    def __init__(self, release_info=None):
        self.release_info = release_info
        splash_image = QPixmap(str(_style_asset_path(self.IMAGE_NAME)))
        if splash_image.isNull():
            splash_image = QPixmap(str(_style_asset_path("splash.png")))

        self.splash_screen = QSplashScreen(splash_image)
        self.splash_screen.setStyleSheet(
            "QSplashScreen { margin-right: 0px; padding-right: 0px; }"
        )
        self.splash_screen.setMask(splash_image.mask())

        width = splash_image.width()
        height = splash_image.height()

        self.splash_progbar = QProgressBar(self.splash_screen)
        self.splash_progbar.setRange(0, 100)
        self.splash_progbar.setTextVisible(False)
        self.splash_progbar.setGeometry(
            QRect(
                int(width * 0.075),
                int(height * 0.782),
                int(width * 0.385),
                max(7, int(height * 0.014)),
            )
        )
        self.splash_progbar.setStyleSheet(
            "QProgressBar {"
            "color: none;"
            "border: 1px solid transparent;"
            "background: rgba(0,0,0,0);"
            "}"
            "QProgressBar::chunk { background: #000000; }"
        )

        self.splash_text = QLabel("Loading MEDUSA Analyzer...", self.splash_screen)
        self.splash_text.setGeometry(
            QRect(
                int(width * 0.075),
                int(height * 0.807),
                int(width * 0.385),
                int(height * 0.065),
            )
        )
        self.splash_text.setStyleSheet(
            "color: #111111;"
            "font-size: 8pt;"
            "font-weight: bold;"
            "font-family: sans-serif, Helvetica, Arial;"
            "background: transparent;"
        )

        self.splash_screen.show()
        QApplication.processEvents()

    def set_state(self, prog_value, prog_text):
        prog_value = int(self.MAX_VALUE * prog_value / 100)
        self.splash_progbar.setValue(prog_value)
        self.splash_text.setText(prog_text)
        QApplication.processEvents()

    def hide(self, parent=None):
        self.splash_screen.finish(parent)


def _style_asset_path(filename: str) -> Path:
    return Path(__file__).resolve().parent / "styles" / filename
