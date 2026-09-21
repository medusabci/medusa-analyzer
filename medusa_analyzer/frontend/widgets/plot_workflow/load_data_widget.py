from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QButtonGroup, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QInputDialog, QLineEdit, QMessageBox, QPushButton, QRadioButton, QScrollArea, QVBoxLayout, QWidget)

from medusa_analyzer.frontend.widgets.plots.recording_ids import (
    is_parameter_recording_file,
    normalize_recording_id,
    recording_ignored_prefixes_from_recordings,
)


class PlotWorkflowLoadDataWidget(QScrollArea):
    changed = Signal()

    # Incializamos el constructor
    def __init__(self, experiment_info: dict, defaults: dict, state: dict):
        del experiment_info
        super().__init__()

        self.state = state
        self.config = defaults.get("load_features", {})
        self.group_definition_config = defaults.get("group_definition", {})
        self.required_folder_name = str(self.config.get("required_folder_name", "derivatives"))
        self.required_config_file = str(self.config.get("required_config_file", "config.json"))
        self.analysis_modes = self.config["analysis_modes"]
        self.option_frames: dict[str, QFrame] = {}

        # Configuración del área del scroll
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self.content = QWidget()
        self.setWidget(self.content)
        root = QVBoxLayout(self.content)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(18)

        title = QLabel(self.page_title())
        title.setObjectName("pageTitle")
        description = QLabel(self.page_description())
        description.setObjectName("muted")
        description.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(description)

        # Cada uno de estos métodos construye una sección diferente de la pantalla
        root.addWidget(self._build_folder_panel())
        root.addWidget(self._build_analysis_panel())
        root.addWidget(self._build_metadata_panel())
        root.addStretch()

        # Recuperamos lo que ya hubiese seleccionado el usuario previamente (si ha ido a otra pantalla, etc.)
        self._restore_state()

    def _build_folder_panel(self) -> QFrame:
        """Función para crear la zona en la que eliges derivatives"""
        panel = QFrame()
        panel.setProperty("role", "surface-panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        heading = QLabel("Feature folder")
        heading.setObjectName("panelTitle")
        layout.addWidget(heading)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self.path_display = QLineEdit()
        self.path_display.setReadOnly(True)
        self.path_display.setPlaceholderText("No derivatives folder selected")
        browse_button = QPushButton("Browse")
        browse_button.setProperty("variant", "secondary")
        browse_button.clicked.connect(self._browse_derivatives_folder)
        row.addWidget(self.path_display, 1)
        row.addWidget(browse_button)
        layout.addLayout(row)
        # Label que se va actualizando
        self.status_label = QLabel("Select a derivatives folder that contains config.json.")
        self.status_label.setObjectName("selectionStatus")
        self.status_label.setProperty("status", "idle")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        return panel

    def _build_analysis_panel(self) -> QFrame:
        """Función para construir el panel con los tipos de análisis."""
        panel = QFrame()
        panel.setProperty("role", "surface-panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        heading = QLabel("Select Analysis Type")
        heading.setObjectName("panelTitle")
        layout.addWidget(heading)

        self.analysis_group = QButtonGroup(self)
        self.analysis_group.setExclusive(True) # agrupamos Rbuttons para que solo uno pueda estar seleccionado a la vez
        self.analysis_group.buttonToggled.connect(lambda _button, checked: self._sync_analysis_mode() if checked else None)

        for i, mode in enumerate(self.analysis_modes):
            option = QFrame()
            option.setProperty("role", "analysis-mode-option")
            option_layout = QVBoxLayout(option)
            option_layout.setContentsMargins(16, 14, 16, 14)
            option_layout.setSpacing(6)

            radio = QRadioButton(str(mode["title"]))
            radio.setProperty("role", "analysis-mode-radio")
            radio.setProperty("analysis_mode", str(mode["id"]))
            radio.setToolTip(str(mode["description"]))
            self.analysis_group.addButton(radio)

            detail = QLabel(str(mode["description"]))
            detail.setObjectName("analysisModeDescription")
            detail.setWordWrap(True)

            option_layout.addWidget(radio)
            option_layout.addWidget(detail)

            # Línea justo encima del último modo
            if i == len(self.analysis_modes) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setFrameShadow(QFrame.Shadow.Sunken)
                layout.addWidget(line)

            layout.addWidget(option)
            self.option_frames[str(mode["id"])] = option

        return panel

    def _build_metadata_panel(self) -> QFrame:
        """Función para crear el panel donde se muestran los metadados"""
        self.metadata_panel = QFrame()
        self.metadata_panel.setProperty("role", "surface-panel")
        self.metadata_layout = QGridLayout(self.metadata_panel)
        self.metadata_layout.setContentsMargins(24, 20, 24, 20)
        self.metadata_layout.setHorizontalSpacing(18)
        self.metadata_layout.setVerticalSpacing(8)
        self.metadata_panel.hide() # inicialmente está oculto (no se ha cargado ninguna carpeta)
        return self.metadata_panel

    def _restore_state(self) -> None:
        """Restaura el modo de análisis y los datos cargados si ya existían en el estado."""
        default_mode = str(self.config.get("default_analysis_mode", "within"))
        selected_mode = str(self.state.get("analysis_mode") or default_mode)
        selected_button = None
        fallback_button = None
        for button in self.analysis_group.buttons():
            mode_id = str(button.property("analysis_mode"))
            if mode_id == default_mode:
                fallback_button = button
            if mode_id == selected_mode:
                selected_button = button
        (selected_button or fallback_button or self.analysis_group.buttons()[0]).setChecked(True)
        self._sync_analysis_mode()

        path = self.state.get("derivatives_path")
        channel_names = self.state.get("channel_names")
        if not path or not channel_names:
            return

        self.path_display.setText(str(path))
        metadata = self.state.get("plot_features_metadata")
        if isinstance(metadata, dict):
            self._show_metadata(metadata)
        self._set_status("Derivatives folder loaded.", "ready")

    def _browse_derivatives_folder(self) -> None:
        # Miramos si ya había una ruta y a continuación abrimos el cuadro de diálogo
        current_path = str(self.state.get("derivatives_path") or "")
        selected_path = QFileDialog.getExistingDirectory(self, "Select derivatives folder", current_path)
        if selected_path:
            self._load_derivatives_folder(Path(selected_path))

    def _load_derivatives_folder(self, path: Path) -> None:
        """Función que comprueba si la carpeta seleccionada es válida"""
        try:
            derivatives_path = path.resolve()
            if not derivatives_path.is_dir():
                raise ValueError("The selected path is not a folder.")
            # Comprobamos que la carpeta se llame derivatives
            if derivatives_path.name.lower() != self.required_folder_name.lower():
                if (derivatives_path / "derivatives").is_dir():
                    derivatives_path = derivatives_path / "derivatives"
                else:
                    raise ValueError("Select the derivatives folder generated by the analysis pipeline.")

            config_path = derivatives_path / self.required_config_file # path donde está el config
            if not config_path.is_file(): # comprobamos que exista el archivo config.json
                raise ValueError(f"The selected derivatives folder must contain {self.required_config_file}.")

            try: # Intentamso leer el json
                config_data = json.loads(config_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"{self.required_config_file} could not be read.") from exc

            # Extraemos canales
            metadata = config_data.get("metadata", {})
            channel_set = metadata.get("channel_set", []) if isinstance(metadata, dict) else []
            if not channel_set:
                raise ValueError(f"{self.required_config_file} does not contain channel names.")
            channel_set = [str(channel) for channel in channel_set]

            feature_files = self._discover_data_files(derivatives_path) # Buscamos archivos correspondientes al workflow
            # Construimos el resumen de metadatos:
            metadata = self._build_metadata(derivatives_path, config_path, config_data, channel_set, feature_files)
            # Guardamos all
            self._apply_loaded_state(derivatives_path, config_path, config_data, channel_set, feature_files, metadata)
        except ValueError as exc:
            self._clear_loaded_state()
            self._set_status(str(exc), "error")
            self.changed.emit()

    def _apply_loaded_state(self, derivatives_path: Path, config_path: Path, config_data: dict[str, Any],
        channel_names: list[str], feature_files: list[str], metadata: dict[str, Any]) -> None:
        path_text = str(derivatives_path)
        self.path_display.setText(path_text)
        self.state["input_data"] = [path_text]
        self.state["derivatives_path"] = path_text
        self.state["pipeline_config_path"] = str(config_path)
        self.state["plot_features_config"] = config_data
        self.state["channel_names"] = channel_names
        self.state[self.data_files_state_key()] = feature_files
        self.state["plot_features_metadata"] = metadata
        # Guardamos los sujetos del config y los recordings analizados desde parameters cuando existen.
        self._store_subjects_and_recordings_from_config(config_data, derivatives_path)
        self._sync_analysis_mode(emit_changed=False)
        self._show_metadata(metadata)
        self._set_status("Derivatives folder loaded.", "ready")
        self.changed.emit()

    def _clear_loaded_state(self) -> None:
        """Función se reseteo."""
        self.path_display.clear()
        self.metadata_panel.hide()
        self.state["input_data"] = []
        for key in ("derivatives_path", "pipeline_config_path", "plot_features_config", "channel_names",
            self.data_files_state_key(), "plot_features_metadata", "plot_features_subjects", "plot_features_recordings",
            "plot_features_recording_ignored_prefixes"):
            self.state.pop(key, None)

    def _sync_analysis_mode(self, emit_changed: bool = True) -> None:
        # Averiguamos cuál es el modo marcado
        button = self.analysis_group.checkedButton()
        if button is None:
            mode_id = str(self.config.get("default_analysis_mode", "within"))
        else:
            mode_id = str(button.property("analysis_mode"))

        self.state["analysis_mode"] = mode_id # lo guardamos en el estado
        if mode_id == "nocomparison":
            self.state["workflow_skip_steps"] = ["group_definition", "group_assignment", "data_assignment"]
        else:
            self.state["workflow_skip_steps"] = []
        for option_mode, frame in self.option_frames.items(): # recalculamos estilo tras selección
            frame.setProperty("selected", option_mode == mode_id)
            frame.style().unpolish(frame)
            frame.style().polish(frame)
        if emit_changed:
            self.changed.emit()

    def _set_status(self, text: str, status: str) -> None:
        self.status_label.setText(text) # cambiamos el texto de la label de estado
        self.status_label.setProperty("status", status) # estado ready o error
        self.status_label.style().unpolish(self.status_label) # estilo
        self.status_label.style().polish(self.status_label) # estilo

    def _show_metadata(self, metadata: dict[str, Any]) -> None:
        """Función para mostrar los metadatos"""
        # Vamos sacando uno a uno los elementos del grid.
        while self.metadata_layout.count():
            item = self.metadata_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not metadata:
            self.metadata_panel.hide()
            return

        for index, (label, value) in enumerate(metadata.items()):
            name = QLabel(str(label))
            name.setObjectName("metricLabel")
            metric = QLabel(self._format_value(value))
            metric.setObjectName("metricValue")
            metric.setWordWrap(True)
            self.metadata_layout.addWidget(name, (index // 3) * 2, index % 3)
            self.metadata_layout.addWidget(metric, (index // 3) * 2 + 1, index % 3)
        self.metadata_panel.show()

    def _build_metadata(self, derivatives_path: Path, config_path: Path, config_data: dict[str, Any],
        channel_names: list[str], feature_files: list[str]) -> dict[str, Any]:
        config_metadata = config_data.get("metadata") if isinstance(config_data.get("metadata"), dict) else {}
        return {"Derivatives folder": derivatives_path.name,
            "Config file": config_path.name,
            "Channels": len(channel_names),
            "Channel names": channel_names,
            "Subjects": config_metadata.get("subjects", []),
            "Sessions": config_metadata.get("sessions", []),
            "Selected features": config_data.get("selected_features", []),
            "Feature files": len(feature_files)}

    @classmethod
    def page_title(cls) -> str:
        return "Load feature data"

    @classmethod
    def page_description(cls) -> str:
        return "Select the derivatives folder generated by a previous analysis pipeline."

    @classmethod
    def data_files_state_key(cls) -> str:
        return "feature_files"

    def _discover_data_files(self, derivatives_path: Path) -> list[str]:
        # Obtenemos las extensiones permitidas de archivos
        allowed_extensions = {str(ext).lower() for ext in self.config.get("allowed_extensions", [])}
        files: list[str] = []
        # Buscamos recursivamente en todas las carpetas y subcarpetas de derivatives
        for file_path in derivatives_path.rglob("*"):
            if not file_path.is_file() or file_path.name == self.required_config_file: # ignoramos config.json
                continue
            if allowed_extensions and file_path.suffix.lower() not in allowed_extensions: # filtramos por extensión
                continue
            files.append(str(file_path))
        return sorted(files)

    def _store_subjects_and_recordings_from_config(self, config_data: dict[str, Any],
        derivatives_path: Path | None = None) -> None:
        def subject_name(recording: dict[str, Any]) -> str:
            """Función para poner bien los nombres de los sujetos. """
            subject = str(recording.get("subject", "")).strip()
            if not subject:
                return ""
            if subject.startswith("sub-"):
                return subject
            return f"sub-{subject}"

        selected_recordings = config_data.get("selected_recordings", [])
        ignored_prefixes = recording_ignored_prefixes_from_recordings(selected_recordings)
        subjects = [subject_name(recording) for recording in selected_recordings]
        recordings = self._recordings_from_derivatives(derivatives_path, ignored_prefixes)
        if not recordings:
            recordings = [normalize_recording_id(str(recording.get("relative_path") or recording.get("path") or ""),
                ignored_prefixes)
                for recording in selected_recordings]

        self.state["plot_features_subjects"] = sorted({subject for subject in subjects if subject})
        self.state["plot_features_recordings"] = sorted({recording for recording in recordings if recording})
        self.state["plot_features_recording_ignored_prefixes"] = list(ignored_prefixes)

    @staticmethod
    def _recordings_from_parameter_files(derivatives_path: Path | None,
        ignored_prefixes: tuple[str, ...]) -> list[str]:
        if derivatives_path is None:
            return []

        search_path = derivatives_path / "parameters"
        if not search_path.is_dir():
            return []

        recordings = []
        for file_path in search_path.rglob("*"):
            if file_path.is_file() and is_parameter_recording_file(file_path):
                recordings.append(normalize_recording_id(str(file_path), ignored_prefixes))
        return sorted({recording for recording in recordings if recording})

    @staticmethod
    def _recordings_from_segmented_files(derivatives_path: Path | None,
        ignored_prefixes: tuple[str, ...]) -> list[str]:
        if derivatives_path is None:
            return []

        search_path = derivatives_path / "segmented"
        if not search_path.is_dir():
            return []

        recordings = []
        for file_path in search_path.rglob("*"):
            stem = file_path.stem
            if file_path.is_file() and "_band-" in stem and "_segment-" in stem:
                recordings.append(normalize_recording_id(str(file_path), ignored_prefixes))
        return sorted({recording for recording in recordings if recording})

    @classmethod
    def _recordings_from_derivatives(cls, derivatives_path: Path | None,
        ignored_prefixes: tuple[str, ...]) -> list[str]:
        return cls._recordings_from_parameter_files(derivatives_path, ignored_prefixes)

    def before_next(self) -> bool:
        if str(self.state.get("analysis_mode") or "") != "nocomparison":
            return True

        recordings = self.state.get("plot_features_recordings")
        available_recordings = [str(recording) for recording in recordings] if isinstance(recordings, list) else []
        if not available_recordings:
            QMessageBox.warning(self, "No recordings available",
                f"No recordings were found in {self.required_config_file}.")
            return False

        selected_recording = available_recordings[0]
        if len(available_recordings) > 1:
            stored_recording = str(self.state.get("plot_features_nocomparison_recording") or "")
            current_index = available_recordings.index(stored_recording) if stored_recording in available_recordings else 0
            selected_subjects, accepted = QInputDialog.getItem(self, "Select recording",
                "Subject:", self.state["plot_features_subjects"], 0, False)
            if not accepted:
                return False
            self.state["plot_features_subjects"] = selected_subjects

            selected_recording, accepted = QInputDialog.getItem(self, "Select recording",
                "Recording:", available_recordings, current_index, False)
            if not accepted:
                return False
            selected_recording = str(selected_recording)


        saturation = int(self.group_definition_config.get("default_color_saturation", 220))
        value = int(self.group_definition_config.get("default_color_value", 225))
        group_color = QColor.fromHsv(0, saturation, value).name().upper()
        group_id = "group_1"

        self.state["plot_features_nocomparison_recording"] = selected_recording
        self.state["groups"] = {group_id: {"group_name": selected_recording,
            "group_color": group_color,
            "subjects": [],
            "files": [selected_recording]}}
        self.state["group_assignment"] = {"target": "recordings",
            "items_by_group": {group_id: [selected_recording]},
            "group_by_item": {selected_recording: group_id}}
        self.state["data_assignment"] = {"target": "recordings",
            "selected_items": [selected_recording]}
        self.state["plot_selected_recordings"] = [selected_recording]
        self.state.pop("plot_selected_subjects", None)
        return True

    @staticmethod
    def _format_value(value: Any) -> str:
        """Función para sacar valores bonitos en pantalla."""
        if isinstance(value, (list, tuple, set)):
            if not value:
                return "None"
            return ", ".join(str(item) for item in value)
        return str(value)

    def can_continue(self) -> bool:
        derivatives_path = self.state.get("derivatives_path")
        config_path = self.state.get("pipeline_config_path")
        # Permite continuar si hay derivatives, config.json, canales y modo de análisis elegido.
        return (bool(derivatives_path) and bool(config_path) and bool(self.state.get("channel_names"))
            and bool(self.state.get("analysis_mode")) and Path(str(derivatives_path)).is_dir()
            and Path(str(config_path)).is_file())


PlotFeaturesLoadDataWidget = PlotWorkflowLoadDataWidget

__all__ = ["PlotFeaturesLoadDataWidget", "PlotWorkflowLoadDataWidget"]
