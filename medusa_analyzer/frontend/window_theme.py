from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QWidget


logger = logging.getLogger(__name__)

TITLE_BAR_COLOR = "#181215"
TITLE_BAR_TEXT_COLOR = "#F7F1F3"
TITLE_BAR_BORDER_COLOR = "#3A2931"


def _colorref(hex_color: str) -> int:
    color = hex_color.strip().lstrip("#")
    if len(color) != 6:
        raise ValueError(f"Invalid color: {hex_color}")
    red = int(color[0:2], 16)
    green = int(color[2:4], 16)
    blue = int(color[4:6], 16)
    return red | (green << 8) | (blue << 16)


def apply_windows_title_bar_theme(window: QWidget) -> None:
    if sys.platform != "win32":
        return

    try:
        import ctypes

        hwnd = ctypes.c_void_p(int(window.winId()))
        dark_mode = ctypes.c_int(1)
        caption_color = ctypes.c_int(_colorref(TITLE_BAR_COLOR))
        text_color = ctypes.c_int(_colorref(TITLE_BAR_TEXT_COLOR))
        border_color = ctypes.c_int(_colorref(TITLE_BAR_BORDER_COLOR))

        dwm = ctypes.windll.dwmapi
        for attribute in (20, 19):
            result = dwm.DwmSetWindowAttribute(
                hwnd,
                attribute,
                ctypes.byref(dark_mode),
                ctypes.sizeof(dark_mode),
            )
            if result == 0:
                break

        for attribute, value in (
            (35, caption_color),
            (36, text_color),
            (34, border_color),
        ):
            dwm.DwmSetWindowAttribute(
                hwnd,
                attribute,
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
    except Exception:
        logger.debug("Could not apply Windows title bar theme", exc_info=True)
