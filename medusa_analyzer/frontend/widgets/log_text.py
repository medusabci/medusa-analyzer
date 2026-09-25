from PySide6.QtGui import QColor, QPalette, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextEdit


def append_log_line(log_area: QTextEdit, message: str, color: QColor | None = None) -> None:
    if color is not None and color.isValid():
        text_color = QColor(color)
    else:
        text_color = log_area.palette().color(QPalette.ColorRole.Text)

    cursor = log_area.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    if not log_area.document().isEmpty():
        cursor.insertBlock()

    format_ = QTextCharFormat()
    format_.setForeground(text_color)
    cursor.insertText(str(message), format_)
    log_area.setTextCursor(cursor)
    log_area.verticalScrollBar().setValue(log_area.verticalScrollBar().maximum())
