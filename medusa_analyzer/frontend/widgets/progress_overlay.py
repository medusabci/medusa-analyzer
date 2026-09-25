from PySide6.QtCore import Property, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from medusa_analyzer.frontend.utils import append_log_line

class ProgressOverlay(QFrame):
    def __init__(self, parent: QWidget, show_log: bool = True):
        super().__init__(parent)
        self.show_log = show_log
        self._error_color = QColor("#FFB6C2")
        self._warning_color = QColor("#F6C177")
        self.setObjectName("progressOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.panel = QFrame(self)
        self.panel.setObjectName("progressWindow")
        self.panel.setProperty("role", "progress-window")
        self.panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        shadow = QGraphicsDropShadowEffect(self.panel)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 14)
        shadow.setColor(QColor(0, 0, 0, 170))
        self.panel.setGraphicsEffect(shadow)

        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(30, 24, 30, 26)
        panel_layout.setSpacing(0)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        self.window_title = QLabel("Progress")
        self.window_title.setObjectName("progressWindowTitle")
        header_layout.addWidget(self.window_title)
        header_layout.addStretch()

        self.close_button = QPushButton("Close")
        self.close_button.setObjectName("progressCloseButton")
        self.close_button.setProperty("variant", "secondary")
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.clicked.connect(self.hide)

        panel_layout.addLayout(header_layout)
        panel_layout.addSpacing(16)

        self.label = QLabel("Processing your request. Please wait...")
        self.label.setObjectName("progressTitle")
        self.label.setWordWrap(True)

        self.progress = QProgressBar()
        self.progress.setObjectName("overlayProgressBar")
        self.progress.setRange(0, 100)
        self.progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        panel_layout.addWidget(self.label)
        panel_layout.addSpacing(14)
        panel_layout.addWidget(self.progress)

        if self.show_log:
            self.log_area = QTextEdit()
            self.log_area.setObjectName("progressLogArea")
            self.log_area.setReadOnly(True)
            self.log_area.setMinimumHeight(150)
            self.log_area.setMaximumHeight(150)
            self.log_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            panel_layout.addSpacing(16)
            panel_layout.addWidget(self.log_area)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 18, 0, 0)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        panel_layout.addSpacing(30)
        panel_layout.addLayout(button_layout)

        self._update_panel_width()
        self._center_panel()
        self.hide()

    def add_log_message(self, message: str, role: str = "info"):
        """Appends a message to the log area with a specific style."""
        if not self.show_log:
            return

        color = None
        if role == "error":
            color = self.errorColor
        elif role == "warning":
            color = self.warningColor

        append_log_line(self.log_area, message, color)

    def start_process(self, text: str) -> None:
        self.label.setText(text)
        self.progress.setValue(0)
        if self.show_log:
            self.log_area.clear()
        self.close_button.hide()
        self.setGeometry(self.parentWidget().rect())
        self._update_panel_width()
        self._center_panel()
        self.raise_()
        self.show()

    def finish_process(self, summary: str | None = None) -> None:
        self.label.setText('Process finished')
        if self.show_log and summary:
            self.add_log_message('----------- SUMMARY -----------')
            self.add_log_message(summary)
        self.close_button.show()

    def _update_panel_width(self) -> None:
        parent = self.parentWidget()
        if not parent:
            return

        available_width = max(420, parent.width() - 96)
        self.panel.setFixedWidth(min(1080, available_width))
        self.panel.adjustSize()

    def _center_panel(self) -> None:
        left = max(0, (self.width() - self.panel.width()) // 2)
        top = max(0, (self.height() - self.panel.height()) // 2)
        self.panel.move(left, top)

    def get_error_color(self) -> QColor:
        return QColor(self._error_color)

    def set_error_color(self, color: QColor) -> None:
        if color.isValid():
            self._error_color = QColor(color)

    def get_warning_color(self) -> QColor:
        return QColor(self._warning_color)

    def set_warning_color(self, color: QColor) -> None:
        if color.isValid():
            self._warning_color = QColor(color)

    errorColor = Property(QColor, get_error_color, set_error_color)
    warningColor = Property(QColor, get_warning_color, set_warning_color)

    def resizeEvent(self, event):
        if self.parentWidget():
            self.setGeometry(self.parentWidget().rect())
            self._update_panel_width()
            self._center_panel()
        super().resizeEvent(event)
