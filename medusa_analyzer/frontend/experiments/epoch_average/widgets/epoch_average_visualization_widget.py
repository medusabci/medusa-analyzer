from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from medusa_analyzer.frontend.widgets.plots import (
    EpochAveragePlot,
    EpochDataIndex,
    prepare_grouped_epoch_data,
)


class EpochAverageVisualizationWidget(QScrollArea):
    changed = Signal()

    def __init__(self, experiment_info: dict, defaults: dict, state: dict):
        del experiment_info
        super().__init__()

        self.state = state
        self.config = defaults.get("plots", {})
        self.plot_types = list(self.config.get("available_plot_types", []))
        self._refreshing = False
        self._data_index: EpochDataIndex | None = None
        self._data_index_key = ""
        self.dynamic_controls: dict[str, dict[str, Any]] = {}
        self.last_export = {"width": 8.0, "height": 5.0, "dpi": 300, "path": ""}

        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self.content = QWidget()
        self.setWidget(self.content)
        root = QVBoxLayout(self.content)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(18)

        title = QLabel("Plot visualization")
        title.setObjectName("pageTitle")
        description = QLabel("Configure the average of aligned epochs for the selected groups.")
        description.setObjectName("muted")
        description.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(description)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        splitter.addWidget(self._build_control_panel())
        splitter.addWidget(self._build_figure_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([360, 720])

        self.status_label = QLabel("")
        self.status_label.setObjectName("selectionStatus")
        self.status_label.setProperty("status", "idle")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        self._refresh_from_state()

    def _build_control_panel(self) -> QScrollArea:
        control_scroll = QScrollArea()
        control_scroll.setWidgetResizable(True)
        control_scroll.setFrameShape(QFrame.Shape.NoFrame)

        control_panel = QFrame()
        control_panel.setProperty("role", "surface-panel")
        control_layout = QVBoxLayout(control_panel)
        control_layout.setContentsMargins(20, 18, 20, 18)
        control_layout.setSpacing(12)
        control_scroll.setWidget(control_panel)

        plot_panel = QFrame()
        plot_panel.setProperty("role", "plot-type-panel")
        plot_layout = QVBoxLayout(plot_panel)
        plot_layout.setContentsMargins(16, 14, 16, 14)
        plot_layout.setSpacing(8)
        plot_label = QLabel("Plot type")
        plot_label.setObjectName("plotTypeTitle")
        plot_select_label = QLabel("Select")
        plot_select_label.setObjectName("plotTypeSelectLabel")
        self.plot_combo = QComboBox()
        self.plot_combo.setProperty("role", "plot-type-combo")
        for plot_info in self.plot_types:
            self.plot_combo.addItem(str(plot_info.get("title", plot_info.get("id", "Plot"))),
                str(plot_info.get("id", "")))
        if not self.plot_types:
            self.plot_combo.addItem("No compatible plot", "")
            self.plot_combo.setEnabled(False)
        self.plot_combo.currentIndexChanged.connect(lambda _index: self._plot_type_changed())
        plot_layout.addWidget(plot_label)
        plot_layout.addWidget(plot_select_label)
        plot_layout.addWidget(self.plot_combo)
        control_layout.addWidget(plot_panel)

        options_tabs = QTabWidget()
        options_tabs.setProperty("role", "plot-control-tabs")

        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        general_layout.setContentsMargins(14, 14, 14, 14)
        general_layout.setSpacing(12)

        channel_header = QHBoxLayout()
        channel_title = QLabel("Channels")
        channel_title.setObjectName("panelTitle")
        average_all_button = QPushButton("Average all")
        average_all_button.setProperty("variant", "secondary")
        clear_channels_button = QPushButton("Clear")
        clear_channels_button.setProperty("variant", "ghost")
        average_all_button.clicked.connect(self._select_all_channels)
        clear_channels_button.clicked.connect(lambda _checked=False: (self.channel_table.clearSelection(),
            self._sync_plot_config()))
        channel_header.addWidget(channel_title)
        channel_header.addStretch()
        channel_header.addWidget(average_all_button)
        channel_header.addWidget(clear_channels_button)
        general_layout.addLayout(channel_header)

        channel_note = QLabel("Select one or more channels. Multiple selected channels will be averaged.")
        channel_note.setObjectName("assignmentInstruction")
        channel_note.setWordWrap(True)
        general_layout.addWidget(channel_note)

        self.channel_table = QTableWidget()
        self.channel_table.setProperty("role", "assignment-table")
        self.channel_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.channel_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.channel_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.channel_table.verticalHeader().hide()
        self.channel_table.horizontalHeader().hide()
        self.channel_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.channel_table.itemSelectionChanged.connect(self._sync_plot_config)
        general_layout.addWidget(self.channel_table)

        band_label = QLabel("Band")
        band_label.setObjectName("panelTitle")
        self.band_combo = QComboBox()
        self.band_combo.currentIndexChanged.connect(lambda _index: self._sync_plot_config())
        general_layout.addWidget(band_label)
        general_layout.addWidget(self.band_combo)
        general_layout.addStretch()

        visualization_tab = QWidget()
        visualization_layout = QVBoxLayout(visualization_tab)
        visualization_layout.setContentsMargins(14, 14, 14, 14)
        visualization_layout.setSpacing(12)
        visualization_title = QLabel("Visualization options")
        visualization_title.setObjectName("panelTitle")
        self.dynamic_widget = QWidget()
        self.dynamic_layout = QGridLayout(self.dynamic_widget)
        self.dynamic_layout.setContentsMargins(0, 0, 0, 0)
        self.dynamic_layout.setHorizontalSpacing(10)
        self.dynamic_layout.setVerticalSpacing(8)
        visualization_layout.addWidget(visualization_title)
        visualization_layout.addWidget(self.dynamic_widget)
        visualization_layout.addStretch()

        options_tabs.addTab(general_tab, "General options")
        options_tabs.addTab(visualization_tab, "Visualization")
        control_layout.addWidget(options_tabs, 1)
        control_layout.addStretch()
        return control_scroll

    def _build_figure_panel(self) -> QFrame:
        figure_panel = QFrame()
        figure_panel.setProperty("role", "plot-preview-panel")
        figure_layout = QVBoxLayout(figure_panel)
        figure_layout.setContentsMargins(12, 12, 12, 12)

        figure_header = QHBoxLayout()
        figure_title = QLabel("Figure")
        figure_title.setObjectName("panelTitle")
        export_button = QPushButton("Export")
        export_button.setProperty("variant", "primary")
        export_button.setProperty("role", "plot-export-button")
        export_button.clicked.connect(self._export_figure)
        figure_header.addWidget(figure_title)
        figure_header.addStretch()
        figure_header.addWidget(export_button)
        figure_layout.addLayout(figure_header)

        self.figure = Figure(figsize=(8, 5), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(420)
        figure_layout.addWidget(self.canvas, 1)

        self.export_status = QLabel("")
        self.export_status.setObjectName("selectionStatus")
        self.export_status.setProperty("status", "idle")
        self.export_status.setWordWrap(True)
        figure_layout.addWidget(self.export_status)
        return figure_panel

    def _refresh_from_state(self) -> None:
        self._refreshing = True
        try:
            self._populate_channel_table()
            self._populate_band_combo()
            self._restore_general_config()
            self._rebuild_dynamic_controls()
        finally:
            self._refreshing = False
        self._sync_plot_config(emit_changed=False)

    def _populate_channel_table(self) -> None:
        channels = self._channel_names()
        columns = 4 if len(channels) > 12 else max(1, min(3, len(channels)))
        rows = max(1, (len(channels) + columns - 1) // columns)

        self.channel_table.blockSignals(True)
        try:
            self.channel_table.clearSelection()
            self.channel_table.clear()
            self.channel_table.setColumnCount(columns)
            self.channel_table.setRowCount(rows)
            for index, channel_name in enumerate(channels):
                item = QTableWidgetItem(str(channel_name))
                item.setData(Qt.ItemDataRole.UserRole, index)
                self.channel_table.setItem(index // columns, index % columns, item)
            for column in range(columns):
                self.channel_table.horizontalHeader().setSectionResizeMode(
                    column, self.channel_table.horizontalHeader().ResizeMode.Stretch)
            self._fit_table_height_to_contents(self.channel_table)
        finally:
            self.channel_table.blockSignals(False)

    def _populate_band_combo(self) -> None:
        bands = self._bands_from_config()
        bands = self._filter_bands_with_epoch_data(bands)

        self.band_combo.blockSignals(True)
        try:
            self.band_combo.clear()
            for band in bands:
                self.band_combo.addItem(str(band["title"]), str(band["id"]))
            if not bands:
                self.band_combo.addItem("No compatible band", "")
                self.band_combo.setEnabled(False)
            else:
                self.band_combo.setEnabled(True)
        finally:
            self.band_combo.blockSignals(False)

    def _restore_general_config(self) -> None:
        stored = self.state.get("epoch_average_plot_config", {})
        if not isinstance(stored, dict):
            stored = {}

        plot_type = str(stored.get("plot_type") or "")
        if plot_type:
            index = self.plot_combo.findData(plot_type)
            if index >= 0:
                self.plot_combo.setCurrentIndex(index)

        band_id = str(stored.get("selected_band") or "")
        if band_id:
            index = self.band_combo.findData(band_id)
            if index >= 0:
                self.band_combo.setCurrentIndex(index)

        channels = self._channel_names()
        selected_channels = stored.get("selected_channels")
        if isinstance(selected_channels, list):
            self._select_channels([int(channel) for channel in selected_channels if str(channel).isdigit()])
        else:
            self._select_channels(list(range(len(channels))))

    def _plot_type_changed(self) -> None:
        self._rebuild_dynamic_controls()
        self._sync_plot_config()

    def _rebuild_dynamic_controls(self) -> None:
        while self.dynamic_layout.count():
            item = self.dynamic_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.dynamic_controls = {}
        plot_info = self._plot_info()
        params = list(plot_info.get("default_params", {}).get("visualization", [])) if plot_info else []
        current_plot_id = str(self.plot_combo.currentData() or "")
        stored_config = self.state.get("epoch_average_plot_config", {})
        stored_params = stored_config.get("visualization", {}) if isinstance(stored_config, dict) else {}
        if not isinstance(stored_params, dict) or stored_config.get("plot_type") != current_plot_id:
            stored_params = {}

        for row, param in enumerate(params):
            param_id = str(param.get("id", ""))
            param_type = str(param.get("type", "text"))
            label = QLabel(str(param.get("title", param_id)))
            self.dynamic_layout.addWidget(label, row, 0)
            default_value = deepcopy(param.get("default"))
            value = stored_params.get(param_id, default_value)

            if param_type == "checkbox":
                control = QCheckBox()
                control.setChecked(bool(value))
                control.toggled.connect(lambda _checked: self._sync_plot_config())
                self.dynamic_layout.addWidget(control, row, 1)
            elif param_type == "int":
                control = QSpinBox()
                control.setRange(int(param.get("min", 0)), int(param.get("max", 9999)))
                control.setValue(int(value))
                control.valueChanged.connect(lambda _value: self._sync_plot_config())
                self.dynamic_layout.addWidget(control, row, 1)
            elif param_type == "float":
                control = QDoubleSpinBox()
                control.setRange(float(param.get("min", -999999.0)), float(param.get("max", 999999.0)))
                control.setDecimals(3)
                control.setSingleStep(float(param.get("step", 0.1)))
                control.setValue(float(value))
                control.valueChanged.connect(lambda _value: self._sync_plot_config())
                self.dynamic_layout.addWidget(control, row, 1)
            elif param_type == "combo":
                control = QComboBox()
                for option in param.get("options", []):
                    control.addItem(str(option.get("title", option.get("id", ""))), str(option.get("id", "")))
                index = control.findData(str(value))
                if index >= 0:
                    control.setCurrentIndex(index)
                control.currentIndexChanged.connect(lambda _index: self._sync_plot_config())
                self.dynamic_layout.addWidget(control, row, 1)
            elif param_type == "range":
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0, 0, 0, 0)
                min_input = QLineEdit()
                max_input = QLineEdit()
                min_input.setPlaceholderText("Auto")
                max_input.setPlaceholderText("Auto")
                if isinstance(value, list) and len(value) == 2:
                    min_input.setText("" if value[0] is None else str(value[0]))
                    max_input.setText("" if value[1] is None else str(value[1]))
                min_input.textChanged.connect(lambda _text: self._sync_plot_config())
                max_input.textChanged.connect(lambda _text: self._sync_plot_config())
                row_layout.addWidget(min_input)
                row_layout.addWidget(max_input)
                control = (min_input, max_input)
                self.dynamic_layout.addWidget(row_widget, row, 1)
            else:
                control = QLineEdit()
                control.setText(str(value))
                control.textChanged.connect(lambda _text: self._sync_plot_config())
                self.dynamic_layout.addWidget(control, row, 1)

            self.dynamic_controls[param_id] = {"control": control, "type": param_type}

        self.dynamic_layout.setColumnStretch(1, 1)

    def _sync_plot_config(self, *_: Any, emit_changed: bool = True) -> None:
        if self._refreshing:
            return

        plot_id = str(self.plot_combo.currentData() or "")
        selected_band = self.band_combo.currentData()
        selected_channels = sorted(set(
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.channel_table.selectedItems()
            if isinstance(item.data(Qt.ItemDataRole.UserRole), int)
        ))

        visualization = {}
        for param_id, data in self.dynamic_controls.items():
            control = data["control"]
            control_type = data["type"]
            if control_type == "checkbox":
                visualization[param_id] = control.isChecked()
            elif control_type in ("int", "float"):
                visualization[param_id] = control.value()
            elif control_type == "combo":
                visualization[param_id] = control.currentData()
            elif control_type == "range":
                values = []
                for input_widget in control:
                    text = input_widget.text().strip()
                    if not text:
                        values.append(None)
                        continue
                    try:
                        values.append(float(text))
                    except ValueError:
                        values.append(None)
                visualization[param_id] = values
            else:
                visualization[param_id] = control.text()

        self.state["epoch_average_plot_config"] = {
            "plot_type": plot_id,
            "selected_channels": selected_channels,
            "selected_band": selected_band,
            "visualization": visualization,
        }

        self._draw_plot(plot_id, str(selected_band or ""), selected_channels, visualization)
        self.canvas.draw_idle()
        self._update_status(plot_id, str(selected_band or ""), selected_channels)

        if emit_changed:
            self.changed.emit()

    def _draw_plot(self, plot_id: str, band_id: str, selected_channels: list[int],
        visualization: dict[str, Any]) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        try:
            if not plot_id:
                self._draw_empty_plot(ax, visualization, "No compatible plot selected.")
                return
            if plot_id != "epoch_average":
                self._draw_empty_plot(ax, visualization, f"{plot_id} plotting is not available.")
                return
            if not band_id:
                self._draw_empty_plot(ax, visualization, "Select a band before plotting.")
                return
            if not selected_channels:
                self._draw_empty_plot(ax, visualization, "Select at least one channel before plotting.")
                return

            data_index = self._data_index_for_state()
            prepared_data = prepare_grouped_epoch_data(self.state, band_id, selected_channels, data_index)
            if not prepared_data.has_observations():
                self._draw_empty_plot(ax, visualization, "No epochs found for this band and selection.")
                return

            plot = EpochAveragePlot(ax, visualization)
            plot.load_prepared_data(prepared_data)
            plot.draw(prepared_data.colors_by_name())
        except Exception as error:
            self._draw_empty_plot(ax, visualization, str(error))
        finally:
            self.figure.tight_layout()

    def _draw_empty_plot(self, ax, visualization: dict[str, Any], message: str) -> None:
        ax.set_title(str(visualization.get("title") or ""), fontsize=int(visualization.get("title_size", 14)),
            fontweight=str(visualization.get("title_weight", "normal")))
        ax.set_xlabel(str(visualization.get("x_label") or ""), fontsize=int(visualization.get("font_size", 10)),
            fontweight=str(visualization.get("font_weight", "normal")))
        ax.set_ylabel(str(visualization.get("y_label") or ""), fontsize=int(visualization.get("font_size", 10)),
            fontweight=str(visualization.get("font_weight", "normal")))
        ax.text(0.5, 0.5, message, transform=ax.transAxes, ha="center", va="center",
            color="#756F77", fontsize=12, wrap=True)
        ax.grid(True, linestyle="--", alpha=0.3)

    def _update_status(self, plot_id: str, band_id: str, selected_channels: list[int]) -> None:
        if not plot_id:
            text, status = "Select a compatible plot type.", "error"
        elif not band_id:
            text, status = "Select a band before plotting.", "error"
        elif not selected_channels:
            text, status = "Select at least one channel before plotting.", "error"
        else:
            text, status = "Epoch-average plot ready.", "ready"
        self.status_label.setText(text)
        self.status_label.setProperty("status", status)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _plot_info(self) -> dict[str, Any] | None:
        plot_id = str(self.plot_combo.currentData() or "")
        for plot_info in self.plot_types:
            if str(plot_info.get("id")) == plot_id:
                return plot_info
        return None

    def _channel_names(self) -> list[str]:
        channels = self.state.get("channel_names")
        if isinstance(channels, list) and channels:
            return [str(channel) for channel in channels]

        config_data = self.state.get("plot_features_config")
        metadata = config_data.get("metadata") if isinstance(config_data, dict) else {}
        channel_set = metadata.get("channel_set") if isinstance(metadata, dict) else []
        return [str(channel) for channel in channel_set] if isinstance(channel_set, list) else []

    def _bands_from_config(self) -> list[dict[str, str]]:
        config_data = self.state.get("plot_features_config")
        preprocessing = config_data.get("preprocessing") if isinstance(config_data, dict) else {}
        bands = preprocessing.get("selected_frequency_bands") if isinstance(preprocessing, dict) else []
        normalized = self._normalize_bands(bands)
        if normalized:
            return normalized

        data_index = self._data_index_for_state()
        band_ids = sorted(data_index.available_band_ids(), key=lambda band: 0 if band.lower() == "broadband" else 1)
        return [{"id": band_id, "title": self._band_title(band_id)} for band_id in band_ids]

    def _filter_bands_with_epoch_data(self, bands: list[dict[str, str]]) -> list[dict[str, str]]:
        data_index = self._data_index_for_state()
        if not data_index.records:
            return bands
        return [band for band in bands if data_index.has_band(band["id"])]

    @staticmethod
    def _normalize_bands(bands: Any) -> list[dict[str, str]]:
        normalized = []
        for band in bands if isinstance(bands, list) else []:
            if not isinstance(band, dict):
                continue
            band_id = str(band.get("id") or band.get("title") or "").strip()
            if not band_id:
                continue
            normalized.append({"id": band_id, "title": str(band.get("title") or EpochAverageVisualizationWidget._band_title(band_id))})
        return sorted(normalized, key=lambda band: 0 if band["id"].lower() == "broadband" else 1)

    @staticmethod
    def _band_title(band_id: str) -> str:
        return "Broadband" if str(band_id).lower() == "broadband" else str(band_id).replace("_", " ").title()

    def _data_index_for_state(self) -> EpochDataIndex:
        derivatives_path = str(self.state.get("derivatives_path") or "")
        ignored_prefixes = self.state.get("plot_features_recording_ignored_prefixes")
        ignored_key = ",".join(str(prefix) for prefix in ignored_prefixes) if isinstance(ignored_prefixes, list) else ""
        data_index_key = f"{derivatives_path}|{ignored_key}"
        if self._data_index is None or self._data_index_key != data_index_key:
            self._data_index = EpochDataIndex.from_state(self.state)
            self._data_index_key = data_index_key
        return self._data_index

    def _select_all_channels(self) -> None:
        self._select_channels(list(range(len(self._channel_names()))))
        self._sync_plot_config()

    def _select_channels(self, channel_indices: list[int]) -> None:
        self.channel_table.clearSelection()
        wanted = set(channel_indices)
        for row in range(self.channel_table.rowCount()):
            for column in range(self.channel_table.columnCount()):
                item = self.channel_table.item(row, column)
                if item is not None and item.data(Qt.ItemDataRole.UserRole) in wanted:
                    item.setSelected(True)

    @staticmethod
    def _fit_table_height_to_contents(table: QTableWidget) -> None:
        table.resizeRowsToContents()
        frame_height = table.frameWidth() * 2
        header_height = table.horizontalHeader().height() if table.horizontalHeader().isVisible() else 0
        rows_height = sum(table.rowHeight(row) for row in range(table.rowCount()) if not table.isRowHidden(row))
        table.setMinimumHeight(frame_height + header_height + rows_height)

    def _export_figure(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Export plot")
        layout = QGridLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)

        width_spin = QDoubleSpinBox()
        width_spin.setRange(1.0, 40.0)
        width_spin.setDecimals(1)
        width_spin.setSingleStep(0.5)
        width_spin.setValue(float(self.last_export.get("width", 8.0)))
        height_spin = QDoubleSpinBox()
        height_spin.setRange(1.0, 40.0)
        height_spin.setDecimals(1)
        height_spin.setSingleStep(0.5)
        height_spin.setValue(float(self.last_export.get("height", 5.0)))
        dpi_spin = QSpinBox()
        dpi_spin.setRange(72, 1200)
        dpi_spin.setValue(int(self.last_export.get("dpi", 300)))
        path_input = QLineEdit()
        path_input.setText(str(self.last_export.get("path") or ""))
        path_input.setPlaceholderText("Select export path")
        browse_button = QPushButton("Browse")
        browse_button.setProperty("variant", "secondary")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)

        def browse_path() -> None:
            current_path = path_input.text().strip() or "epoch_average.png"
            selected_path, _ = QFileDialog.getSaveFileName(dialog, "Export plot", current_path, "PNG image (*.png)")
            if selected_path:
                path_input.setText(selected_path)

        browse_button.clicked.connect(browse_path)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        layout.addWidget(QLabel("Width"), 0, 0)
        layout.addWidget(width_spin, 0, 1)
        layout.addWidget(QLabel("Height"), 1, 0)
        layout.addWidget(height_spin, 1, 1)
        layout.addWidget(QLabel("DPI"), 2, 0)
        layout.addWidget(dpi_spin, 2, 1)
        layout.addWidget(QLabel("Path"), 3, 0)
        layout.addWidget(path_input, 3, 1)
        layout.addWidget(browse_button, 3, 2)
        layout.addWidget(buttons, 4, 0, 1, 3)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        path_text = path_input.text().strip()
        if not path_text:
            self.export_status.setText("Select an export path.")
            self.export_status.setProperty("status", "error")
            self.export_status.style().unpolish(self.export_status)
            self.export_status.style().polish(self.export_status)
            return

        try:
            self.figure.set_size_inches(width_spin.value(), height_spin.value())
            Path(path_text).parent.mkdir(parents=True, exist_ok=True)
            self.figure.savefig(path_text, dpi=dpi_spin.value())
            self.last_export = {"width": width_spin.value(), "height": height_spin.value(),
                "dpi": dpi_spin.value(), "path": path_text}
            self.export_status.setText(f"Saved to {path_text}")
            self.export_status.setProperty("status", "ready")
        except Exception as error:
            self.export_status.setText(str(error))
            self.export_status.setProperty("status", "error")

        self.export_status.style().unpolish(self.export_status)
        self.export_status.style().polish(self.export_status)

    def on_step_activated(self) -> None:
        self._data_index = None
        self._refresh_from_state()

    def can_continue(self) -> bool:
        config = self.state.get("epoch_average_plot_config", {})
        return (isinstance(config, dict)
            and bool(config.get("plot_type"))
            and bool(config.get("selected_band"))
            and bool(config.get("selected_channels")))


__all__ = ["EpochAverageVisualizationWidget"]
