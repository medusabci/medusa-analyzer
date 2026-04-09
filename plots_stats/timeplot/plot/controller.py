from PySide6 import QtCore, QtWidgets
import numpy as np
import medusa
import medusa.ecg
import os
import json
from PySide6.QtUiTools import loadUiType
from plots_stats.plot_utils import *
from medusa.analysis.time_plot.time_plot import TimeSeriesPlot, TimePlotManager

medusa_path = os.path.dirname(medusa.__file__)
timeplot_ui_path = os.path.join(medusa_path, "analysis", "time_plot", "time_plot.ui")

class PlotController(QtCore.QObject):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.view.controller = self

        self.recording = None # actualizes when loading a valid recording to plot
        self.fs = self.view.main_module.controller.fs
        self.channel_list = self.view.main_module.controller.channel_list
        self.template_ui_path = 'plots_stats/timeplot/plot/tab_template.ui'

        self._tabs_created = False
        self.view.shown.connect(self.create_tabs)

    def load_ui(self, path, parent=None):
        """Load the tab_template UI from the given path."""
        form_class, base_class = loadUiType(path)
        widget = base_class(parent) if parent is not None else base_class()
        ui = form_class()
        ui.setupUi(widget)
        return widget

    def select_all_channels(self, tab, sig):
        """Select all channels in the channel list."""
        list_widget = tab.findChild(QtWidgets.QListWidget, "channelListWidget")
        if list_widget is None:
            return

        list_widget.blockSignals(True)
        list_widget.selectAll()
        list_widget.blockSignals(False)

        self.on_channels_selected(tab, sig)
        self.update_plot(tab)

    def create_tabs(self):
        """Create one tab per recording file."""
        self.filtered_files = self.view.main_module.controller.file_path_to_plot
        if self.filtered_files is None:
            return

        self.view.main_module.loading.show()
        self.view.main_module.loading.set_progress(0, self.view.main_module)

        # Normalize to list of paths
        if isinstance(self.filtered_files, str):
            file_paths = [self.filtered_files]
        else:
            try:
                file_paths = list(self.filtered_files)
            except TypeError:
                file_paths = [self.filtered_files]

        tab_widget = self.view.tab_widget
        while tab_widget.count() > 0:
            tab_widget.removeTab(0)

        # Load json config
        signals_json, self.plots_json = load_plot_json_files(os.path.dirname(__file__))
        experiment_type = self.view.main_module.controller.plot_option
        self.type_signal = self.view.main_module.controller.signal_type

        # If signal_type comes as list/tuple, keep first one
        if isinstance(self.type_signal, (list, tuple)):
            if not self.type_signal:
                print("[WARN] No signal type selected.")
                self.view.main_module.loading.finish()
                return
            self.type_signal = self.type_signal[0]

        signal_data_list = signals_json.get(experiment_type, [])
        if not signal_data_list:
            print(f"[WARN] No config found for experiment type '{experiment_type}'.")
            self.view.main_module.loading.finish()
            return

        self.features_data = signal_data_list[0]

        total = max(len(file_paths), 1)

        for idx, file_path in enumerate(file_paths):
            if self.type_signal not in self.features_data:
                print(f"[WARN] Signal '{self.type_signal}' not available for '{experiment_type}'. Skipping.")
                continue

            plot_type = "TimePlot"
            plot_type_data = self.plots_json.get(plot_type)
            if not plot_type_data:
                print(f"[WARN] Plot type '{plot_type}' not found in type_plots.json")
                continue

            if self.type_signal not in plot_type_data.get("allowed_signals", []):
                print(f"[WARN] Signal '{self.type_signal}' not allowed for plot type '{plot_type}'")
                continue

            # Load recording
            recording = medusa.components.Recording.load(file_path)

            # Defaults from available_data.json
            base_plot_params = self.features_data[self.type_signal]["Plot_params"]

            # Metadata from type_plots.json
            plot_params_meta = plot_type_data["Plot_params"]

            # Merge defaults
            merged_params = {}
            for key, meta in plot_params_meta.items():
                default_value = meta.get("default", None)

                if isinstance(default_value, str) and default_value.startswith("Plot_params."):
                    ref_key = default_value.split(".")[-1]
                    default_value = base_plot_params.get(ref_key, "")

                merged_params[key] = {
                    "type": meta.get("type", "text"),
                    "label": meta.get("label", key),
                    "default": default_value,
                    "options": meta.get("options", []),
                    "min": meta.get("min", 0),
                    "max": meta.get("max", 100),
                    "step": meta.get("step", 0.1),
                }

            # Create tab
            print('tab_created')
            tab = self.load_ui(self.template_ui_path, parent=tab_widget)
            tab._file_path = file_path
            tab._recording = recording

            self.setup_channel_list(tab, self.type_signal)
            self.setup_conditions_list(tab)
            self.setup_events_list(tab)

            # Needed by build_dynamic_controls
            tab._available_plot_types = {
                plot_type: {
                    "plot_params_meta": merged_params
                }
            }
            tab._current_plot_type = plot_type
            tab._plot_type = plot_type

            # Optional title label
            title_label = tab.findChild(QtWidgets.QLabel, "titleLabel")
            if title_label is not None:
                title_label.setText(f"{self.type_signal} - {os.path.basename(file_path)}")

            # Build controls
            controls_widget = tab.findChild(QtWidgets.QWidget, "controlWidget")
            build_dynamic_controls(self, controls_widget, merged_params, tab)

            # If only one plot type exists, disable combobox
            type_combo = tab.findChild(QtWidgets.QComboBox, "TypePlotcomboBox")
            if type_combo is not None:
                type_combo.setEnabled(False)

            # Insert empty placeholder content if needed
            placeholder = tab.findChild(QtWidgets.QWidget, "plotPlaceholder")
            layout = placeholder.layout()
            if layout is None:
                layout = QtWidgets.QVBoxLayout(placeholder)
                placeholder.setLayout(layout)

            # Connect buttons
            export_btn = tab.findChild(QtWidgets.QPushButton, "exportButton")
            if export_btn is not None:
                export_btn.clicked.connect(lambda checked=False, t=tab: self.export_figure(t))

            update_btn = tab.findChild(QtWidgets.QPushButton, "updateButton")
            if update_btn is not None:
                update_btn.clicked.connect(lambda checked=False, t=tab: self.update_plot(t))

            # Add splitter
            self.convert_to_splitter(tab)

            # Add tab
            self.view.add_tab(tab, os.path.basename(file_path))
            self._tabs_created = True

            # Initial plot
            QtCore.QTimer.singleShot(0, lambda t=tab: self.update_plot(t))

            progress = ((idx + 1) / total) * 100
            self.view.main_module.loading.set_progress(progress, self.view.main_module)

        self.view.main_module.loading.finish()

    def setup_channel_list(self, tab, sig):
        """ Config the channel list """

        list_widget = tab.findChild(QtWidgets.QListWidget, "channelListWidget")
        channels = self.view.main_module.controller.channel_list

        if not channels:
            print('Channels not found')
            return

        # Add channels to list
        list_widget.clear()
        for ch in channels:
            item = QtWidgets.QListWidgetItem(ch)
            list_widget.addItem(item)

        list_widget.selectAll()
        tab._selected_channels = {sig: list(range(list_widget.count()))}
        self.on_channels_selected(tab, sig)
        list_widget.itemSelectionChanged.connect(lambda: self.on_channels_selected(tab, sig))

        avg_all_btn = tab.findChild(QtWidgets.QPushButton, "averageallpushButton")
        if avg_all_btn is not None:
            avg_all_btn.clicked.connect(
                lambda checked=False, t=tab, s=sig: self.select_all_channels(t, s)
            )

    def on_channels_selected(self, tab, sig):
        """Read the selected channels and store its indices"""
        list_widget = tab.findChild(QtWidgets.QListWidget, "channelListWidget")
        selected_indexes = [list_widget.row(item) for item in list_widget.selectedItems()]
        tab._selected_channels[sig] = selected_indexes
        print(f"Selected channel indices for param '{sig}': {selected_indexes}")

    def setup_conditions_list(self, tab):
        """Configure the conditions combobox with the available conditions in each tab."""
        conds = tab._recording.marks.app_settings.get("conditions", {})
        cond_labels_used = getattr(tab._recording.marks, "conditions_labels", [])
        has_conditions = bool(conds) and bool(cond_labels_used)
        tab.findChild(QtWidgets.QListWidget, "conditionslistWidget").setVisible(has_conditions)
        tab.findChild(QtWidgets.QLabel, "conditionsLabel").setVisible(has_conditions)
        if not has_conditions:
            tab._selected_conditions = []
            return
        setup_marks_listwidget(tab=tab, widget_name="conditionslistWidget", items_dict=conds,
            used_labels=cond_labels_used, selected_attr="_selected_conditions", on_change=self.on_conditions_selected)
    def on_conditions_selected(self, tab):
        """Read selected conditions from the QListWidget."""
        list_widget = tab.findChild(QtWidgets.QListWidget, "conditionslistWidget")
        if list_widget is None:
            tab._selected_conditions = []
            return

        selected = [item.text() for item in list_widget.selectedItems()]
        tab._selected_conditions = selected
        print("Selected conditions:", selected)

    def build_conditions_dict(self, tab):
        """Build the conditions_dict based on user selection."""
        conds_all = tab._recording.marks.app_settings.get("conditions", {})
        cond_labels = tab._recording.marks.conditions_labels
        cond_times = tab._recording.marks.conditions_times
        selected_conds = getattr(tab, "_selected_conditions", [])

        if not selected_conds:
            return None

        conds_filtered = {k: v for k, v in conds_all.items() if k in selected_conds}
        valid_labels = [conds_all[c]["label"] for c in selected_conds]
        cond_labels_filtered = [lbl for lbl in cond_labels if lbl in valid_labels]
        cond_times_filtered = [t for lbl, t in zip(cond_labels, cond_times) if lbl in valid_labels]

        return {"conditions": conds_filtered, "conditions_labels": cond_labels_filtered, "conditions_times": cond_times_filtered}

    def build_events_dict(self, tab):
        """Build the events_dict based on user selection."""
        events_all  = tab._recording.marks.app_settings.get("events", {})
        event_labels  = tab._recording.marks.events_labels
        event_times  = tab._recording.marks.events_times
        selected_events  = getattr(tab, "_selected_events", [])

        if not selected_events:
            return None

        events_filtered  = {k: v for k, v in events_all.items() if k in selected_events}
        valid_event_labels  = [events_all[c]["label"] for c in selected_events]
        event_labels_filtered  = [lbl for lbl in event_labels if lbl in valid_event_labels ]
        event_times_filtered  = [t for lbl, t in zip(event_labels, event_times) if lbl in valid_event_labels ]

        return {"events": events_filtered, "events_labels": event_labels_filtered ,
                "events_times": event_times_filtered }

    def setup_events_list(self, tab):
        """Configure the events combobox with the available events in each tab."""
        events = tab._recording.marks.app_settings.get("events", {})
        event_labels_used = getattr(tab._recording.marks, "events_labels", [])
        has_events = bool(event_labels_used) and bool(event_labels_used)
        tab.findChild(QtWidgets.QListWidget, "eventslistWidget").setVisible(has_events)
        tab.findChild(QtWidgets.QLabel, "eventsLabel").setVisible(has_events)
        if not has_events:
            tab._selected_events = []
            return
        setup_marks_listwidget(tab=tab, widget_name="eventslistWidget", items_dict=events,
            used_labels=event_labels_used, selected_attr="_selected_events", on_change=self.on_events_selected)

    def on_events_selected(self, tab):
        """Read selected events from the QListWidget."""
        list_widget = tab.findChild(QtWidgets.QListWidget, "eventslistWidget")
        if list_widget is None:
            tab._selected_events = []
            return

        selected = [item.text() for item in list_widget.selectedItems()]
        tab._selected_events = selected
        print("Selected events:", selected)

    def _clear_layout(self, layout):
        """Helper to delete all items/widgets from a layout."""
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
            else:
                # If item is a layout, clear it recursively
                sub = item.layout()
                if sub is not None:
                    self._clear_layout(sub)

    def update_plot(self, tab):
        params = {
            key: get_widget_value(param_type, widget)
            for key, (param_type, widget) in tab._param_widgets.items()
        }
        print("PARAMS:", params)

        recording = tab._recording
        signal_attr = self.type_signal.lower()

        times = getattr(recording, signal_attr).times
        signal = getattr(recording, signal_attr).signal
        ch_labels = self.view.main_module.controller.channel_list
        selected_idxs = tab._selected_channels[self.type_signal]
        n_channels = len(selected_idxs)

        conditions_dict = self.build_conditions_dict(tab)
        events_dict = self.build_events_dict(tab)

        time_plot = TimeSeriesPlot(
            n_cha=n_channels,
            cha_labels=[ch_labels[i] for i in selected_idxs],
            cha_to_show=n_channels,
            reverse_channels=True
        )

        time_plot.add_data(
            times=times,
            data=signal[:, selected_idxs],
            data_label=self.type_signal,
            cha_idx=np.arange(0, n_channels),
            time_ref=None,
            conditions_dict=conditions_dict,
            events_dict=events_dict,
            style_params=None
        )

        fig = time_plot.canvas.figure
        ax = time_plot.canvas.axes

        title = params.get("title", "")
        title_size = params.get("title_size", 8)
        title_weight = params.get("title_weight", "normal")
        fig.suptitle(title, fontsize=title_size, fontweight=title_weight)

        xlabel = params.get("x_label", "")
        ylabel = params.get("y_label", "")

        ax.set_xlabel(xlabel, fontweight="normal")
        ax.set_ylabel(ylabel, fontweight="normal")

        fig.tight_layout()
        fig.canvas.draw_idle()

        placeholder = tab.findChild(QtWidgets.QWidget, "plotPlaceholder")
        layout = placeholder.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(placeholder)
            placeholder.setLayout(layout)

        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        widgets_to_hide = ["btn_download", "label", "edit_dpi"]
        for w in widgets_to_hide:
            widget = getattr(time_plot, w, None)
            if widget:
                widget.hide()

        layout.addWidget(time_plot)

    def convert_to_splitter(self, tab):
        control_panel = tab.findChild(QtWidgets.QFrame, "controlPanelArea")
        plot_placeholder = tab.findChild(QtWidgets.QWidget, "plotPlaceholder")

        parent_layout = tab.layout()

        # 1. Remove widgets from existing layout
        parent_layout.removeWidget(control_panel)
        parent_layout.removeWidget(plot_placeholder)

        # 2. Create splitter
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(control_panel)
        splitter.addWidget(plot_placeholder)

        # 3. Add splitter to the main tab layout
        parent_layout.addWidget(splitter)

        # 4. Give proper stretch so the panel nunca desaparece
        splitter.setStretchFactor(0, 0)  # Panel de config fijo
        splitter.setStretchFactor(1, 1)  # Plot ocupa el resto

        # 5. Minimum width for control panel
        control_panel.setMinimumWidth(260)

    def export_figure(self, tab):
        placeholder = tab.findChild(QtWidgets.QWidget, "plotPlaceholder")
        layout = placeholder.layout()

        time_plot_widget = None
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if isinstance(w, TimeSeriesPlot):
                time_plot_widget = w
                break

        fig = (time_plot_widget.canvas.figure if time_plot_widget is not None else None)
        export_figure_generic(view=self.view, fig=fig, suggested_name="Timeplot", warn_if_none=True)
