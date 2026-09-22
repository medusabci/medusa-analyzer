from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from medusa_analyzer.frontend.utils import save_pipeline_config


class ReportWidget(QScrollArea):
    changed = Signal()

    # Clase base para montar la estructura comun del report. La clase conoce
    # titulo, subtitulo, metadata y deja hooks para que las subclases anadan
    # secciones especificas del experimento.
    def __init__(self, config: dict[str, Any], state: dict[str, Any], title: str, description: str):
        super().__init__()
        self.config = config
        self.state = state
        self.pipeline_running = bool(getattr(self, "pipeline_running", False))
        self.title_text = title
        self.description_text = description
        self._ensure_output_paths()
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.content = QWidget()
        self.root = QVBoxLayout(self.content)
        self.root.setContentsMargins(4, 4, 12, 4)
        self.root.setSpacing(16)
        self.setWidget(self.content)
        self.refresh()

    def on_step_activated(self) -> None:
        # Al entrar en el paso regeneramos el report para reflejar el estado
        # actual del workflow.
        self._ensure_output_paths()
        self.refresh()

    def refresh(self) -> None:
        # Limpiamos y reconstruimos todo el contenido visual del report.
        while self.root.count():
            item = self.root.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        title = QLabel(self.title_text)
        title.setObjectName("pageTitle")
        subtitle = QLabel(self.description_text)
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        self.root.addWidget(title)
        self.root.addWidget(subtitle)

        for section in self._sections():
            if section is not None:
                self.root.addWidget(section)

        self.root.addStretch()

    def _sections(self) -> list[QWidget]:
        sections: list[QWidget] = []
        for builder in self._section_builders():
            section = builder()
            if section is not None:
                sections.append(section)
        return sections

    def _section_builders(self) -> list:
        builders = []
        if self.config.get("include_metadata", True):
            builders.append(lambda: self._metadata_section(self.state.get("metadata") or {}))
        builders.extend(self._additional_section_builders())
        if self._output_section_enabled():
            builders.append(self._output_section)
        return builders

    def _additional_section_builders(self) -> list:
        # Por defecto intentamos usar los hooks estandar de preprocessing y
        # features. Las subclases pueden sobreescribir este metodo para decidir
        # dinamicamente que secciones incluir.
        return [self._preprocessing_section, self._features_section]

    def _preprocessing_section(self) -> QFrame | None:
        return None

    def _features_section(self) -> QFrame | None:
        return None

    def _output_section_enabled(self) -> bool:
        return bool(self.config.get("include_output_selector", True))

    def _output_path_state_key(self) -> str:
        return "output_path"

    def _output_child_folder_name(self) -> str:
        folder = self.config.get("output_child_folder", "derivatives")
        return str(folder or "").strip().strip("/\\")

    def _default_output_root(self) -> Path | None:
        input_data = self.state.get("input_data") or []
        if not input_data:
            return None

        first_path = Path(str(input_data[0]))
        if first_path.exists() and first_path.is_dir():
            return first_path
        return first_path.parent

    def _output_path_from_root(self, root_path: Path) -> Path:
        child_folder = self._output_child_folder_name()
        return root_path / child_folder if child_folder else root_path

    def _set_output_root_path(self, root_path: str | Path, mode: str) -> None:
        root = Path(str(root_path))
        self.state["output_root_path"] = str(root)
        self.state[self._output_path_state_key()] = str(self._output_path_from_root(root))
        self.state["output_path_mode"] = mode

    def _ensure_output_paths(self) -> None:
        if not self._output_section_enabled():
            return

        current_root = self.state.get("output_root_path")
        current_output = self.state.get(self._output_path_state_key())
        mode = self.state.get("output_path_mode")

        if mode != "custom":
            default_root = self._default_output_root()
            if default_root is not None:
                self._set_output_root_path(default_root, "default")
                return

        if current_root and not current_output:
            self._set_output_root_path(str(current_root), str(mode or "custom"))
            return

        if not current_root and not current_output:
            self.state.pop("output_root_path", None)
            self.state.pop(self._output_path_state_key(), None)
            self.state.pop("output_path_mode", None)

    def _output_path_validation(self) -> tuple[bool, str]:
        if not self._output_section_enabled():
            return True, ""

        root_text = str(self.state.get("output_root_path") or "")
        output_text = str(self.state.get(self._output_path_state_key()) or "")
        if not root_text or not output_text:
            return False, "Select a valid output folder before running the pipeline."

        root = Path(root_text)
        output_path = Path(output_text)
        try:
            if not root.exists() or not root.is_dir():
                return False, "Selected output folder does not exist."
            if output_path.exists() and not output_path.is_dir():
                return False, f"Cannot create {output_path.name} because a file with that name already exists."
        except OSError as exc:
            return False, f"Selected output folder is not valid: {exc}"

        child_folder = self._output_child_folder_name()
        if child_folder:
            return True, f"Results will be saved in the {child_folder} folder."
        return True, "Results will be saved in the selected folder."

    def _select_output_root(self) -> None:
        current_root = str(self.state.get("output_root_path") or self._default_output_root() or "")
        selected_root = QFileDialog.getExistingDirectory(self, "Change output folder", current_root)
        if not selected_root:
            return

        self._set_output_root_path(selected_root, "custom")
        self.refresh()
        self.changed.emit()

    def _output_section(self) -> QFrame:
        self._ensure_output_paths()
        valid, status_text = self._output_path_validation()
        output_path = str(self.state.get(self._output_path_state_key()) or "No output path selected.")

        panel = QFrame()
        panel.setProperty("role", "summary-section")
        layout = QGridLayout(panel)
        layout.setContentsMargins(24, 20, 24, 20)
        heading = QLabel("Output")
        heading.setObjectName("panelTitle")
        layout.addWidget(heading, 0, 0, 1, 2)

        key = QLabel("Results folder")
        key.setObjectName("summaryLabel")
        path_label = QLabel(output_path)
        path_label.setObjectName("outputPathLabel")
        path_label.setWordWrap(True)
        select_button = QPushButton("Select output folder")
        select_button.setProperty("variant", "secondary")
        select_button.clicked.connect(self._select_output_root)

        path_row = QHBoxLayout()
        path_row.setContentsMargins(0, 0, 0, 0)
        path_row.setSpacing(10)
        path_row.addWidget(path_label, 1)
        path_row.addWidget(select_button)

        status = QLabel(status_text)
        status.setObjectName("selectionStatus")
        status.setProperty("status", "ready" if valid else "error")
        status.setWordWrap(True)

        layout.addWidget(key, 1, 0)
        layout.addLayout(path_row, 1, 1)
        layout.addWidget(status, 2, 0, 1, 2)
        layout.setColumnStretch(1, 1)
        return panel

    def can_continue(self) -> bool:
        self._ensure_output_paths()
        valid, _ = self._output_path_validation()
        return valid and not self.pipeline_running

    def before_next(self) -> bool:
        return self._save_config_json(mark_completed=False)

    def run_pipeline(self) -> None:
        self._save_config_json(mark_completed=True)

    def _save_config_json(self, mark_completed: bool) -> bool:
        if self.pipeline_running or not self.can_continue():
            return False

        self.pipeline_running = True
        self.state.pop("pipeline_config_error", None)
        if mark_completed:
            self.state["completion_status"] = "incompleted"
        self.changed.emit()

        try:
            output_path = self.state[self._output_path_state_key()]
            config_path = Path(output_path) / "config.json"
            self.state["pipeline_config_path"] = str(config_path)
            if mark_completed:
                self.state["completion_status"] = "completed"
            save_pipeline_config(self.state, output_path)
            return True
        except Exception as exc:
            if mark_completed:
                self.state["completion_status"] = "incompleted"
            self.state["pipeline_config_error"] = str(exc)
            return False
        finally:
            self.pipeline_running = False
            self.refresh()
            self.changed.emit()

    def _metadata_section(self, metadata: dict[str, Any]) -> QFrame:
        if not metadata:
            return self._section("Metadata", [("Status", "No data loaded yet.")])

        rows = []
        for key, value in metadata.items():
            if isinstance(value, (list, tuple, set)):
                value = ", ".join(str(item) for item in value)
            elif isinstance(value, float):
                value = f"{value:g}"
            rows.append((str(key).replace("_", " ").title(), str(value)))
        return self._section("Metadata", rows)

    def _section(self, title: str, rows: list[tuple[str, str]]) -> QFrame:
        panel = QFrame()
        panel.setProperty("role", "summary-section")
        layout = QGridLayout(panel)
        layout.setContentsMargins(24, 20, 24, 20)
        heading = QLabel(title)
        heading.setObjectName("panelTitle")
        layout.addWidget(heading, 0, 0, 1, 2)

        for row_index, (label, value) in enumerate(rows, start=1):
            key = QLabel(label)
            key.setObjectName("summaryLabel")
            detail = QLabel(value)
            detail.setWordWrap(True)
            layout.addWidget(key, row_index, 0)
            layout.addWidget(detail, row_index, 1)

        layout.setColumnStretch(1, 1)
        return panel
