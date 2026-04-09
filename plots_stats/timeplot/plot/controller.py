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
        """ Create the tabs """
        # Aqui la idea es que vamos a crear tantas tabs como files vengan en filtered_files. Ahi tenemos los pathes.
        self.filtered_files = self.view.main_module.controller.file_path_to_plot
        if self.filtered_files is None:
            return

        self.view.main_module.loading.show()
        self.view.main_module.loading.set_progress(0, self.view.main_module)

        # Todo: esto creo que va a haber que cambiarlo teniendo en cuenta como es filtered_files
        try:
            file_iter = list(self.filtered_files)
        except Exception:
            file_iter = [str(self.filtered_files)]

        tab_widget = self.view.tab_widget
        while tab_widget.count() > 0:
            tab_widget.removeTab(0)

        signals_json, self.plots_json = load_plot_json_files(os.path.dirname(__file__))
        experiment_type = self.view.main_module.controller.experiment_type
        self.features_data = signals_json.get(experiment_type, [])[0]

        total = max(len(file_iter), 1)
        self.view.main_module.loading.set_progress((1 / total) * 100, self.view.main_module)

        for idx, file in enumerate(file_iter):
            if file not in self.features_data:
                print(f"[WARN] Parameter '{param}' not found in available_params.json. Skipping.")
                continue

            param_name = self.features_data[param]["Param_name"]
            self.param_name_to_key = {v["Param_name"]: k for k, v in self.features_data.items()}
            base_plot_params = self.features_data[param]["Plot_params"]

            tab = self.load_ui(self.template_ui_path, parent=tab_widget)

            self.setup_channel_list(tab, param)
            self.setup_band_list(tab, param)

            param_bands = self.available_bands.get(param, [])
            if param_bands:
                self.on_band_selected(tab, param, param_bands[0])

            param_key = param
            filtered = tab._filtered_files_bands.get(param_key, {})
            sel = tab._selected_channels.get(param, 0)
            selected_channels = sel if isinstance(sel, (list, tuple, set)) else [int(sel)]
            tab._data_mode = self.detect_data_mode(filtered, selected_channels)

            placeholder = tab.findChild(QtWidgets.QWidget, "plotPlaceholder")
            layout = self._get_or_create_layout(placeholder)

            fig = Figure(figsize=(5, 4))
            canvas = FigureCanvas(fig)
            ax = fig.add_subplot(111)

            title_label = tab.findChild(QtWidgets.QLabel, "titleLabel")
            if title_label:
                title_label.setText(param_name)

            tab._available_plot_types = self._create_available_plot_types(param_name, base_plot_params, plots_json)
            if tab._available_plot_types:
                tab._current_plot_type = next(iter(tab._available_plot_types))
            else:
                tab._current_plot_type = None

            self.filter_plot_types_by_mode(tab, plots_json)
            if tab._current_plot_type not in tab._available_plot_types:
                if tab._available_plot_types:
                    tab._current_plot_type = next(iter(tab._available_plot_types))
                else:
                    print(f"[WARN] No available plots for parameter {param_name}")
                    continue

            # Instantiate initial plot object
            plot_info = tab._available_plot_types[tab._current_plot_type]
            plot_class = plot_info["plot_class"]
            plot_obj = plot_class(ax, plot_info["plot_params_current"], self.view)
            plot_info["plot_obj"] = plot_obj
            tab._plot = plot_obj
            tab._figure = fig
            tab._canvas = canvas
            tab._plot_type = tab._current_plot_type
            tab._plot_params = plot_info["plot_params_meta"]
            tab._plot_params_current = plot_info["plot_params_current"]

            if layout is not None:
                layout.addWidget(canvas)

            controls_widget = tab.findChild(QtWidgets.QWidget, "controlWidget")
            build_dynamic_controls(self, controls_widget, tab._available_plot_types[tab._current_plot_type]["plot_params_meta"], tab)

            tab._force_autolimits = True
            self.view.add_tab(tab, str(param_name)) # First, add the tab to the view
            self.update_plot(tab) # Then update the plot, once the tab is part of the widget hierarchy

            prev_btn = tab.findChild(QtWidgets.QPushButton, "prevButton")
            prev_btn.clicked.connect(self.prev_tab)
            next_btn = tab.findChild(QtWidgets.QPushButton, "nextButton")
            next_btn.clicked.connect(self.next_tab)
            export_btn = tab.findChild(QtWidgets.QPushButton, "exportButton")
            export_btn.clicked.connect(lambda checked, t=tab: self.export_figure(t))
            update_btn = tab.findChild(QtWidgets.QPushButton, "updateButton")
            update_btn.clicked.connect(lambda checked, t=tab: self.update_plot(t))
            stats_btn = tab.findChild(QtWidgets.QPushButton, "statsButton")
            stats_btn.clicked.connect(lambda checked, t=tab: self.stats_report(t))

            # self.view.add_tab(tab, str(param_name))
            self._tabs_created = True

            progress = ((idx + 1) / total) * 100
            self.view.main_module.loading.set_progress(progress, self.view.main_module)

        self.view.main_module.loading.finish()

    # def create_tabs(self):
    #     """ Create the tabs """
    #
    #     self.type_signal = self.view.main_module.controller.signal_type
    #
    #     # Loading screen
    #     self.view.main_module.loading.show()
    #     self.view.main_module.loading.set_progress(0, self.view.main_module)
    #
    #
    #     # Obtain paths of filtered files:
    #     self.filtered_files = self.view.main_module.controller.file_path_to_plot
    #
    #     # Load recording
    #     # TODO: in future versions, load all selected preprocessed recordings and the associate each one to a tab
    #     self.recording = self.recording = medusa.components.Recording.load(self.filtered_files)
    #
    #     tab_widget = self.view.tab_widget
    #     while tab_widget.count() > 0:
    #         tab_widget.removeTab(0)
    #
    #     # Load available_signals.json and type_plots.json to obtain the available plot the selected signal with its default params
    #     signals_json_path = os.path.join(os.path.dirname(__file__), "available_signals.json")
    #     plots_json_path = os.path.join(os.path.dirname(__file__), "type_plots.json")
    #     with open(signals_json_path, "r", encoding="utf-8") as f:
    #         signal_json = json.load(f)
    #     with open(plots_json_path, "r", encoding="utf-8") as f:
    #         plots_json = json.load(f)
    #
    #     plot_option = self.view.main_module.controller.plot_option
    #     signal_plot_data  = signal_json.get(plot_option, [])[0]
    #
    #     # Update loading progress
    #     self.view.main_module.loading.set_progress((1 / len(self.type_signal)) * 100,
    #                                                self.view.main_module)
    #
    #     # For each selected signal, we insert one tab in de TabWidget
    #     # TODO: instead of looping trhough signal, loop through the selected preprocessed recordings in 'loading' step
    #     for sig in self.type_signal:
    #         if sig not in signal_plot_data:
    #             print(f"[WARN] Signal '{sig}' not found in available_signals.json. Skipping.")
    #             continue
    #
    #         base_plot_params = signal_plot_data[sig]["Plot_params"]
    #
    #         # Find the associate plot type
    #         plot_type = None
    #         for ptype, pdata in plots_json.items():
    #             allowed = pdata["allowed_signals"]
    #             if sig in allowed:
    #                 plot_type = ptype
    #                 plot_type_data = pdata
    #                 break
    #         if not plot_type:
    #             print(f"[WARN] No plot type found for '{sig}' in plot_plots.json")
    #             continue
    #         plot_params_meta = plot_type_data["Plot_params"]
    #
    #         # Merge default values
    #         merged_params = {}
    #         for key, meta in plot_params_meta.items():
    #             default_value = meta.get("default", None)
    #
    #             if isinstance(default_value, str) and default_value.startswith("Plot_params."):
    #                 ref_key = default_value.split(".")[-1]
    #                 default_value = base_plot_params.get(ref_key, "")
    #
    #             merged_params[key] = {
    #                 "type": meta.get("type", "text"),
    #                 "label": meta.get("label", key),
    #                 "default": default_value,
    #                 "options": meta.get("options", [])
    #             }
    #
    #         # Create tab
    #         tab = self.load_ui(self.template_ui_path, parent=tab_widget)
    #         self.setup_channel_list(tab, sig)
    #         self.setup_conditions_list(tab)
    #         self.setup_events_list(tab)
    #
    #         # Create plot object based on plot_type
    #         plot_info = tab._available_plot_types[tab._current_plot_type]
    #         plot_class = plot_info["plot_class"]
    #         tab._plot_type = plot_type
    #         tab._plot_type = tab._current_plot_type
    #
    #         if plot_type == "TimePlot":
    #             print("[DEBUG] Creating TimePlot")
    #
    #         # Create dynamic controls for plot parameters in the tab view
    #         controls_widget = tab.findChild(QtWidgets.QWidget, "controlWidget")
    #         build_dynamic_controls(self, controls_widget, tab._available_plot_types[tab._current_plot_type]["plot_params_meta"], tab)
    #
    #         # Insert time_plot UI into the tab's plot area
    #         time_plot_widget = self.load_ui(timeplot_ui_path, parent=tab)
    #         placeholder = tab.findChild(QtWidgets.QWidget, "plotPlaceholder")
    #         layout = placeholder.layout()
    #         if layout is None:
    #             layout = QtWidgets.QVBoxLayout(placeholder)
    #             placeholder.setLayout(layout)
    #         layout.addWidget(time_plot_widget)
    #
    #         # Connect buttons
    #         # prev_btn = tab.findChild(QtWidgets.QPushButton, "prevButton")
    #         # prev_btn.clicked.connect(self.prev_tab)
    #         # next_btn = tab.findChild(QtWidgets.QPushButton, "nextButton")
    #         # next_btn.clicked.connect(self.next_tab)
    #         export_btn = tab.findChild(QtWidgets.QPushButton, "exportButton")
    #         export_btn.clicked.connect(lambda checked, t=tab: self.export_figure(t))
    #         update_btn = tab.findChild(QtWidgets.QPushButton, "updateButton")
    #         update_btn.clicked.connect(lambda checked, t=tab: self.update_plot(t))
    #
    #         # Add splitter
    #         self.convert_to_splitter(tab)
    #
    #         # Add widget to main TabWinget
    #         self.view.add_tab(tab, str(sig))
    #         self._tabs_created = True
    #
    #         QtCore.QTimer.singleShot(0, lambda t=tab: self.update_plot(t))
    #
    #         # Update loading progress
    #         #TODO: recalculate progress bar
    #         # self.view.main_module.loading.set_progress(((param_iter.index(sig) + 2) / len(param_iter)) * 100, self.view.main_module)
    #         self.view.main_module.loading.set_progress(100, self.view.main_module)
    #
    #     # Finish loading
    #     self.view.main_module.loading.finish()

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

    def setup_marks_combobox(self, tab, combo_name, items_dict, used_labels, selected_attr, on_change, placeholder):
        combo_box = tab.findChild(QtWidgets.QComboBox, combo_name)

        if combo_box is None:
            combo_box = replace_with_checkable_combobox(tab, combo_name, placeholder=placeholder)
        elif not isinstance(combo_box, CheckableComboBox):
            combo_box = replace_with_checkable_combobox(tab, combo_name, placeholder=placeholder)

        if combo_box is None:
            print(f"{combo_name} not found.")
            setattr(tab, selected_attr, [])
            return

        if not items_dict:
            print(f"No items found for {combo_name}.")
            combo_box.clear_items()
            setattr(tab, selected_attr, [])
            return

        if not used_labels:
            print(f"No used labels found for {combo_name}.")
            combo_box.clear_items()
            setattr(tab, selected_attr, [])
            return

        used_labels = set(int(l) for l in used_labels)

        filtered_names = [
            name for name, data in items_dict.items()
            if data.get("label", None) in used_labels
        ]

        combo_box.clear_items()

        if not filtered_names:
            setattr(tab, selected_attr, [])
            return

        combo_box.add_checkable_items(filtered_names, checked=True)
        combo_box.update_text()

        setattr(tab, selected_attr, filtered_names)

        try:
            combo_box.checkedItemsChanged.disconnect()
        except (TypeError, RuntimeError):
            pass

        combo_box.checkedItemsChanged.connect(lambda selected, t=tab: on_change(t, selected))

    def setup_conditions_list(self, tab):
        """Configure the conditions combobox with the available conditions in each tab."""
        conds = self.recording.marks.app_settings.get("conditions", {})
        cond_labels_used = getattr(self.recording.marks, "conditions_labels", [])

        self.setup_marks_combobox(tab=tab, combo_name="conditionscomboBox", items_dict=conds, used_labels=cond_labels_used,
            selected_attr="_selected_conditions", on_change=self.on_conditions_selected, placeholder="Select conditions")

    def on_conditions_selected(self, tab, selected=None):
        """Read the selected conditions."""
        if selected is None:
            combo_box = tab.findChild(QtWidgets.QComboBox, "conditionscomboBox")
            if isinstance(combo_box, CheckableComboBox):
                selected = combo_box.checked_items()
            else:
                selected = []
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
        """Configure the events combobox with the available events in each tab."""
        events = self.recording.marks.app_settings.get("events", {})
        event_labels_used = getattr(self.recording.marks, "events_labels", [])

        self.setup_marks_combobox(tab=tab, combo_name="eventscomboBox", items_dict=events, used_labels=event_labels_used,
            selected_attr="_selected_events", on_change=self.on_events_selected, placeholder="Select events")

    def on_events_selected(self, tab, selected=None):
        """Read the selected events."""
        if selected is None:
            combo_box = tab.findChild(QtWidgets.QComboBox, "eventscomboBox")
            if isinstance(combo_box, CheckableComboBox):
                selected = combo_box.checked_items()
            else:
                selected = []
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
