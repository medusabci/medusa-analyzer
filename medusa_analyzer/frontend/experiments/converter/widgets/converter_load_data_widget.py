from pathlib import Path
from typing import Any

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QHBoxLayout,QLabel,QLineEdit,QFrame,QFileDialog,QPushButton,QDialog

from medusa_analyzer.backend.converter.inspect_source import load_converter_source
from medusa_analyzer.frontend.widgets import LoadDataAction, LoadDataWidget, WorkerCall
from medusa_analyzer.frontend.experiments.converter.widgets.other_database_dialog import OtherDatabaseMappingDialog
from medusa_analyzer.frontend.experiments.converter.widgets.other_database_tutorial import (
    OtherDatabaseTutorialOverlay,
)


class ConverterLoadDataWidget(LoadDataWidget):
    def __init__(self, experiment_info: dict, defaults: dict, state: dict):
        load_data_config = defaults.get("load_data", {})
        allowed_extensions = tuple(load_data_config.get("allowed_extensions", ()))

        super().__init__(
            config=load_data_config,  # allowed extensions
            state=state,
            actions=[
                LoadDataAction(
                    id="medusa_files",
                    label="Load MEDUSA Files",
                    select=lambda widget: widget.select_files("Select MEDUSA files"),
                    build_call=lambda paths: WorkerCall(
                        function=load_converter_source,
                        kwargs={"input_data": [Path(path) for path in paths],
                            "validation_type": "files"}),
                    display_names=lambda paths: [Path(path).name for path in paths],
                    status_text=lambda paths: f"Reading {len(paths)} MEDUSA file(s)...",
                    overlay_text="Reading MEDUSA files...",
                ),
                LoadDataAction(id="medusa_studio",
                    label="Load MEDUSA Studio",
                    select=lambda widget: widget.select_directory("Select MEDUSA Studio directory"),
                    build_call=lambda path: WorkerCall(
                        function=load_converter_source,
                        kwargs={"input_data": Path(path),
                            "validation_type": "studio",
                            "extensions": allowed_extensions}),
                    display_names=lambda path: [Path(path).name or str(path)],
                    status_text="Reading folder...",
                    overlay_text="Reading MEDUSA Studio folder...",
                ),
                LoadDataAction(
                    id="other_database",
                    label="Load Other DB",
                    select=lambda widget: None,
                    build_call=lambda _: WorkerCall(function=lambda: None),
                    display_names=lambda _: [],
                    status_text="",
                ),
            ],
            title="Load data",
            description="Select a MEDUSA Studio dataset.",
            metadata_labels={
                "Total files": "Total files",
                "Number of subjects": "Number of subjects",
                "Number of tasks": "Number of tasks",
                "Task list": "Task list",
                "File types": "File types",
                "Sample record": "Sample record",
                "Layout warnings": "Layout warnings",
                "Mapping status": "Mapping status",
            },
        )

        other_db_button = self.action_buttons.get("other_database")
        if other_db_button is not None:
            try:
                other_db_button.clicked.disconnect()
            except (RuntimeError, TypeError):
                pass
            other_db_button.clicked.connect(self._open_other_database_flow)

        # --- New sections for dataset name and output path ---

        self.output_panel = QFrame()
        self.output_panel.setProperty("role", "surface-panel")
        output_layout = QHBoxLayout(self.output_panel)
        output_layout.setContentsMargins(24, 20, 24, 20)

        # Dataset name
        output_layout.addWidget(QLabel("Dataset name:"))
        self.dataset_name_input = QLineEdit()
        self.dataset_name_input.setValidator(QRegularExpressionValidator(QRegularExpression(r"[A-Za-z0-9_]*"), self))
        self.dataset_name_input.textChanged.connect(self._update_full_path)
        output_layout.addWidget(self.dataset_name_input)

        output_layout.addSpacing(20)

        # Output path
        output_layout.addWidget(QLabel("Output path:"))
        self.output_path_display = QLineEdit()
        self.output_path_display.setReadOnly(True)
        self.output_path_display.setStyleSheet("border: none; background-color: transparent;")
        self.base_path = ""
        output_layout.addWidget(self.output_path_display)
        self.select_path_button = QPushButton("...")
        self.select_path_button.clicked.connect(self._select_output_path)
        output_layout.addWidget(self.select_path_button)

        # Add the new panel to the main layout, after the metadata panel
        root_layout = self.content.layout()
        metadata_panel_index = root_layout.indexOf(self.metadata_panel)
        root_layout.insertWidget(metadata_panel_index + 1, self.output_panel)

        self.output_panel.hide()
        self.other_database_tutorial = OtherDatabaseTutorialOverlay(self)


    def _open_other_database_flow(self) -> None:
        self.other_database_tutorial.start(self._open_other_database_dialog)

    def _open_other_database_dialog(self) -> None:
        dialog = OtherDatabaseMappingDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.accepted_payload:
            return
        self._apply_other_database_payload(dialog.accepted_payload)

    def _apply_other_database_payload(self, payload: dict[str, Any]) -> None:
        self._clear_loaded_state()

        scan = payload["scan"]
        mapping = payload["mapping"]
        validation = payload["validation"]
        validation_summary = dict(validation.get("summary", {}))
        summary = {}
        if "Total files" in validation_summary:
            summary["Total files"] = validation_summary["Total files"]
        elif scan.get("file_count") is not None:
            summary["Total files"] = scan["file_count"]
        target_extension = scan.get("target_extension", "")
        if target_extension:
            summary["File types"] = target_extension
        for key in ("Number of subjects", "Number of tasks", "Task list"):
            if key in validation_summary:
                summary[key] = validation_summary[key]
        sample_record = scan.get("sample_record", {})
        summary["Sample record"] = sample_record.get("relative_path", "")
        layout_warnings = scan.get("layout_warnings") or []
        if layout_warnings:
            summary["Layout warnings"] = " ".join(str(warning) for warning in layout_warnings)
        summary["Mapping status"] = "Validated"

        self.files.clear()
        found_files = scan.get("files", [])
        self.files.addItems([record["relative_path"] for record in found_files])

        self._selected_source = scan.get("root_path")
        self.state["source_type"] = "other_database"
        self.state["input_data"] = [scan.get("root_path", "")]
        self.state["metadata"] = summary
        self.state["other_db_scan"] = scan
        self.state["other_db_mapping"] = mapping
        self.state["other_db_validation"] = validation
        self.state["completion_status"] = "incompleted"

        total_files = len(found_files)
        self.status_label.setText(f"Other database mapping ready: {total_files} record(s) found.")
        self.status_label.setProperty("status", "ready")
        self._refresh_status_style()
        self._show_metadata(summary)
        self.changed.emit()

    def _select_output_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self.base_path = path
            self._update_full_path()

    def _update_full_path(self):
        dataset_name = self.dataset_name_input.text().strip()
        if self.base_path and dataset_name:
            self.output_path_display.setText(f"{self.base_path}/{dataset_name}")
        elif self.base_path:
            self.output_path_display.setText(self.base_path)
        else:
            self.output_path_display.clear()
        self.changed.emit()

    def _show_metadata(self, metadata: dict[str, Any]) -> None:
        # For showing/hiding the new output panel.
        super()._show_metadata(metadata)
        if not hasattr(self, "output_panel"):
            return
        if metadata:
            self.output_panel.show()
        else:
            self.output_panel.hide()

    def _clear_loaded_state(self) -> None:
        # For clearing the new panels and input fields.
        super()._clear_loaded_state()
        self.output_panel.hide()
        self.dataset_name_input.clear()
        self.output_path_display.clear()
        self.base_path = ""
        self.state.pop("output_path", None)
        self.state.pop("dataset_name", None)
        self.state.pop("source_type", None)
        self.state.pop("other_db_scan", None)
        self.state.pop("other_db_mapping", None)
        self.state.pop("other_db_validation", None)

    def _update_state(self):
        self.state["output_path"] = self.output_path_display.text().strip()
        self.state["dataset_name"] = self.dataset_name_input.text().strip()

    def can_continue(self) -> bool:
        dataset_name = self.dataset_name_input.text().strip()
        output_path = self.output_path_display.text().strip()
        self._update_state()
        return super().can_continue() and bool(dataset_name) and bool(output_path) and Path(output_path).parent.is_dir()
