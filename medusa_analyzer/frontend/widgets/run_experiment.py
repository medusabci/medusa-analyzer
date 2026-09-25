from typing import Any

from PySide6.QtCore import Property, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QLabel, QProgressBar, QTextEdit, QVBoxLayout, QWidget

from medusa_analyzer.frontend.utils import append_log_line
from medusa_analyzer.frontend.worker import TaskRunner, Worker


class _ProgressLogColors(QFrame):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._error_color = QColor("#FFB6C2")
        self._warning_color = QColor("#F6C177")
        self.setObjectName("progressOverlay")
        self.hide()

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


class RunExperimentWidget(QWidget):
    """Run step for the converter experiment."""

    changed = Signal()

    def __init__(self, experiment_info: dict, defaults: dict, state: dict):
        super().__init__()
        self.experiment_info = experiment_info
        self.defaults = defaults
        self.state = state
        self.runner = TaskRunner()
        self.pipeline_running = False
        self.setObjectName("runExperimentWidget")
        self.log_colors = _ProgressLogColors(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        title_label = QLabel("Run " + self.experiment_info['title'])
        title_label.setObjectName("pageTitle")
        description_label = QLabel(self.experiment_info['subtitle'])
        description_label.setObjectName("muted")
        description_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addSpacing(18)

        progress_panel = QFrame()
        progress_panel.setProperty("role", "surface-panel")
        progress_layout = QVBoxLayout(progress_panel)
        progress_layout.setContentsMargins(24, 22, 24, 22)

        self.status_label = QLabel("Ready to run pipeline.")
        self.status_label.setObjectName("progressTitle")
        self.status_label.setWordWrap(True)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("overlayProgressBar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.log_area = QTextEdit()
        self.log_area.setObjectName("progressLogArea")
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(180)

        progress_layout.addWidget(self.status_label)
        progress_layout.addSpacing(14)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addSpacing(16)
        progress_layout.addWidget(self.log_area)

        layout.addWidget(progress_panel)
        layout.addStretch()

    def log_callback(self, message: str, role: str = "info"):
        """Append a message to the inline conversion log."""
        color = None
        if role == "error":
            color = self.log_colors.errorColor
        elif role == "warning":
            color = self.log_colors.warningColor
        append_log_line(self.log_area, message, color)

    def set_progress(self, value: int):
        """Set the inline progress value."""
        self.progress_bar.setValue(value)

    def clear_logs(self):
        """Clear the inline conversion log."""
        self.log_area.clear()

    def _pipeline_completed(self, result: Any) -> None:
        if isinstance(result, dict) and result.get("valid") is False:
            errors = result.get("errors") or [f"Pipeline {self.experiment_info['title']} finished with errors."]
            self._mark_pipeline_failed("\n".join(str(error) for error in errors))
            return

        self.state["completion_status"] = "completed"
        self.status_label.setText(f"Pipeline {self.experiment_info['title']} finished successfully.")
        self.set_progress(100)

    def _pipeline_failed(self, error: str) -> None:
        self._mark_pipeline_failed(error)

    def _mark_pipeline_failed(self, error: str) -> None:
        self.state["completion_status"] = "incompleted"
        self.log_callback(error, "error")
        self.status_label.setText(f"The pipeline {self.experiment_info['title']} failed. Fix the issue and run it again.")

    def _pipeline_finished(self) -> None:
        self.pipeline_running = False
        self.changed.emit()

    def can_continue(self) -> bool:
        return not self.pipeline_running

    def run_conversion_process(self):
        self.run_pipeline()
