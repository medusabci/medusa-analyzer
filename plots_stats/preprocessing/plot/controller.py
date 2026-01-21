from PySide6 import QtCore, QtWidgets
import numpy as np
import medusa
import medusa.ecg
import os
import json
from PySide6.QtUiTools import loadUiType
from plots_stats.plot_utils import ExportDialog, build_dynamic_controls, export_figure_generic
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
        self.template_ui_path = 'plots_stats/preprocessing/plot/tab_template.ui'

        self._tabs_created = False
        self.view.shown.connect(self.create_tabs)

    def load_ui(self, path, parent=None):
        """Load the tab_template UI from the given path."""
        form_class, base_class = loadUiType(path)
        widget = base_class(parent) if parent is not None else base_class()
        ui = form_class()
        ui.setupUi(widget)
        return widget

    def create_tabs(self):
        """ Create the tabs """

        self.type_signal = self.view.main_module.controller.signal_type

        # Loading screen
        self.view.main_module.loading.show()
        self.view.main_module.loading.set_progress(0, self.view.main_module)


        # Obtain paths of filtered files:
        self.filtered_files = self.view.main_module.controller.file_path_to_plot

        # Load recording
        # TODO: in future versions, load all selected preprocessed recordings and the associate each one to a tab
        self.recording = self.recording = medusa.components.Recording.load(self.filtered_files)

        tab_widget = self.view.tab_widget
        while tab_widget.count() > 0:
            tab_widget.removeTab(0)

        # Load available_signals.json and type_plots.json to obtain the available plot the selected signal with its default params
        signals_json_path = os.path.join(os.path.dirname(__file__), "available_signals.json")
        plots_json_path = os.path.join(os.path.dirname(__file__), "type_plots.json")
        with open(signals_json_path, "r", encoding="utf-8") as f:
            signal_json = json.load(f)
        with open(plots_json_path, "r", encoding="utf-8") as f:
            plots_json = json.load(f)

        plot_option = self.view.main_module.controller.plot_option
        signal_plot_data  = signal_json.get(plot_option, [])[0]

        # Update loading progress
        self.view.main_module.loading.set_progress((1 / len(self.type_signal)) * 100,
                                                   self.view.main_module)

        # For each selected signal, we inset one tab in de TabWidget
        # TODO: instead of looping trhough signal, loop through the selected preprocessed recordings in 'loading' step
        for sig in self.type_signal:
            if sig not in signal_plot_data:
                print(f"[WARN] Signal '{sig}' not found in available_signals.json. Skipping.")
                continue

            base_plot_params = signal_plot_data[sig]["Plot_params"]

            # Find the associate plot type
            plot_type = None
            for ptype, pdata in plots_json.items():
                allowed = pdata["allowed_signals"]
                if sig in allowed:
                    plot_type = ptype
                    plot_type_data = pdata
                    break
            if not plot_type:
                print(f"[WARN] No plot type found for '{sig}' in plot_plots.json")
                continue
            plot_params_meta = plot_type_data["Plot_params"]

            # Merge default values
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
                    "options": meta.get("options", [])
                }

            # Create tab
            tab = self.load_ui(self.template_ui_path, parent=tab_widget)
            self.setup_channel_list(tab, sig)
            self.setup_conditions_list(tab)
            self.setup_events_list(tab)

            # Create plot object based on plot_type
            tab._plot_type = plot_type
            if plot_type == "TimePlot":
                print("[DEBUG] Creating TimePlot")

            # Create dynamic controls for plot parameters in the tab view
            controls_widget = tab.findChild(QtWidgets.QWidget, "TypePlotWidget")
            build_dynamic_controls(self, controls_widget, merged_params, tab)

            # Insert time_plot UI into the tab's plot area
            time_plot_widget = self.load_ui(timeplot_ui_path, parent=tab)
            placeholder = tab.findChild(QtWidgets.QWidget, "plotPlaceholder")
            layout = placeholder.layout()
            if layout is None:
                layout = QtWidgets.QVBoxLayout(placeholder)
                placeholder.setLayout(layout)
            layout.addWidget(time_plot_widget)

            # Connect buttons
            # prev_btn = tab.findChild(QtWidgets.QPushButton, "prevButton")
            # prev_btn.clicked.connect(self.prev_tab)
            # next_btn = tab.findChild(QtWidgets.QPushButton, "nextButton")
            # next_btn.clicked.connect(self.next_tab)
            export_btn = tab.findChild(QtWidgets.QPushButton, "exportButton")
            export_btn.clicked.connect(lambda checked, t=tab: self.export_figure(t))
            update_btn = tab.findChild(QtWidgets.QPushButton, "updateButton")
            update_btn.clicked.connect(lambda checked, t=tab: self.update_plot(t))

            # Add splitter
            self.convert_to_splitter(tab)

            # Add widget to main TabWinget
            self.view.add_tab(tab, str(sig))
            self._tabs_created = True

            QtCore.QTimer.singleShot(0, lambda t=tab: self.update_plot(t))

            # Update loading progress
            #TODO: recalculate progress bar
            # self.view.main_module.loading.set_progress(((param_iter.index(sig) + 2) / len(param_iter)) * 100, self.view.main_module)
            self.view.main_module.loading.set_progress(100, self.view.main_module)


        # Finish loading
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

    def on_channels_selected(self, tab, sig):
        """Read the selected channels and store its indices"""
        list_widget = tab.findChild(QtWidgets.QListWidget, "channelListWidget")
        selected_indexes = [list_widget.row(item) for item in list_widget.selectedItems()]
        tab._selected_channels[sig] = selected_indexes
        print(f"Selected channel indices for param '{sig}': {selected_indexes}")

    def setup_conditions_list(self, tab):
        """Configure the QListWidget with the available conditions in each tab."""
        list_widget = tab.findChild(QtWidgets.QListWidget, "conditionsWidget")

        conds = self.recording.marks.app_settings.get("conditions", {})
        if not conds:
            print("No conditions found in recording.")
            return
        cond_labels_used = getattr(self.recording.marks, "conditions_labels", [])
        if not cond_labels_used:
            print("Recording has no condition labels. No conditions will be shown.")
            list_widget.clear()
            tab._selected_conditions = []
            return

        cond_labels_used = set(int(l) for l in cond_labels_used)

        list_widget.clear()
        filtered_cond_names = []

        # Add filtered condition names
        for cond_name, cond_data in conds.items():
            label = cond_data.get("label", None)
            if label in cond_labels_used:
                item = QtWidgets.QListWidgetItem(cond_name)
                list_widget.addItem(item)
                filtered_cond_names.append(cond_name)

        # Select all by default and store selection
        list_widget.selectAll()
        tab._selected_conditions = list(conds.keys())
        list_widget.itemSelectionChanged.connect(lambda: self.on_conditions_selected(tab))

    def on_conditions_selected(self, tab):
        """Read de selected conditions."""
        list_widget = tab.findChild(QtWidgets.QListWidget, "conditionsWidget")
        selected = [item.text() for item in list_widget.selectedItems()]
        tab._selected_conditions = selected
        print("Selected conditions:", selected)

    def build_conditions_dict(self, tab):
        """Build the conditions_dict based on user selection."""
        conds_all = self.recording.marks.app_settings.get("conditions", {})
        cond_labels = self.recording.marks.conditions_labels
        cond_times = self.recording.marks.conditions_times
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
        events_all  = self.recording.marks.app_settings.get("events", {})
        event_labels  = self.recording.marks.events_labels
        event_times  = self.recording.marks.events_times
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
        """Configure the QListWidget with the available events in each tab."""
        list_widget = tab.findChild(QtWidgets.QListWidget, "eventsWidget")

        events = self.recording.marks.app_settings.get("events", {})
        if not events:
            print("No events found in recording.")
            return

        event_labels_used = getattr(self.recording.marks, "events_labels", [])
        if not event_labels_used:
            print("Recording has no event labels. No events will be shown.")
            list_widget.clear()
            tab._selected_events = []
            return

        event_labels_used = set(int(l) for l in event_labels_used)

        list_widget.clear()
        filtered_event_names = []

        # Add filtered event names
        for ev_name, ev_data in events.items():
            label = ev_data.get("label", None)
            if label in event_labels_used:
                item = QtWidgets.QListWidgetItem(ev_name)
                list_widget.addItem(item)
                filtered_event_names.append(ev_name)

        # Select all by default and store selection
        list_widget.selectAll()
        tab._selected_events = list(events.keys())
        list_widget.itemSelectionChanged.connect(lambda: self.on_events_selected(tab))

    def on_events_selected(self, tab):
        """Read de selected events."""
        list_widget = tab.findChild(QtWidgets.QListWidget, "eventsWidget")
        selected = [item.text() for item in list_widget.selectedItems()]
        tab._selected_events = selected
        print("Selected events:", selected)

    def get_current_params(self, tab):
        params = {}

        for name, (param_type, widget) in tab._param_widgets.items():

            if param_type in ("text", "range", "number"):
                text = widget.text()
                # Si es JSON (lista, tuple, dict), intenta parsearlo
                try:
                    value = json.loads(text)
                except:
                    value = text
                params[name] = value

            elif param_type == "bool":
                params[name] = widget.isChecked()

            elif param_type == "select":
                params[name] = widget.currentText()

        return params

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

        # user parameters
        params = self.get_current_params(tab)
        print("PARAMS:", params)

        recording = self.recording
        times = getattr(recording, self.type_signal[0].lower()).times
        signal = getattr(recording, self.type_signal[0].lower()).signal
        ch_labels = self.view.main_module.controller.channel_list
        selected_idxs = tab._selected_channels[self.type_signal[0]]
        n_channels = len(selected_idxs)

        conditions_dict = self.build_conditions_dict(tab)
        events_dict = self.build_events_dict(tab)

        time_plot = TimeSeriesPlot(
            n_cha=n_channels,
            cha_labels=[ch_labels[i] for i in selected_idxs],
            cha_to_show=n_channels,
            reverse_channels=True
        )

        # Add data
        time_plot.add_data(
            times=times,
            data=signal[:, selected_idxs],
            data_label="EEG",
            cha_idx=np.arange(0, n_channels),
            time_ref=None,
            conditions_dict=conditions_dict,
            events_dict=events_dict,
            style_params=None
        )

        # Title and labels
        fig = time_plot.canvas.figure
        ax = time_plot.canvas.axes  # << EL EJE REAL

        # Title
        title = params.get("title", "")
        fig.suptitle(title, fontsize=8)

        # Axis labels
        xlabel = params.get("x_label", "")
        ylabel = params.get("y_label", "")

        ax.set_xlabel(xlabel, fontweight="normal")
        ax.set_ylabel(ylabel, fontweight="normal")

        fig.tight_layout()
        fig.canvas.draw_idle()

        # Insert the plot widget into the tab's placeholder
        placeholder = tab.findChild(QtWidgets.QWidget, "plotPlaceholder")
        layout = placeholder.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(placeholder)
            placeholder.setLayout(layout)
        ## Clear previous plot widget
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Hide export buttons from time_plot UI
        widgets_to_hide = ["btn_download", "label", "edit_dpi"]
        for w in widgets_to_hide:
            widget = getattr(time_plot, w, None)
            if widget:
                widget.hide()

        # Add the TimeSeriesPlot widget
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
