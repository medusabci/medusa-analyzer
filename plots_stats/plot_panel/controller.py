# python
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import (QFileDialog, QDialog)
from PySide6.QtUiTools import loadUiType
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from plots_stats.plot_panel.plot_classes.base_plot import BasePlot
from plots_stats.plot_panel.plot_classes.psd_plot import PSDPlot
from plots_stats.plot_panel.plot_classes.linear_plot import LinearPlot
from plots_stats.plot_panel.plot_classes.violin_plot import ViolinPlot
from plots_stats.plot_panel.plot_classes.scatter_plot import ScatterPlot
from plots_stats.plot_panel.plot_classes.erp_plot import ERPPlot
from plots_stats.plot_utils import ExportDialog, build_dynamic_controls, export_figure_generic
from functools import partial
import re, os, json
import numpy as np
import scipy
from scipy.io import loadmat
from collections import defaultdict


class TabbedPlotWidgetController(QtCore.QObject):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.template_ui_path = 'plots_stats/plot_panel/tab_template.ui'

        self._tabs_created = False
        self.view.shown.connect(self.create_tabs)
        self.available_bands = []
        self.simple_plots = {"PSDPlot", "LinearPlot", "ViolinPlot", "ERPPlot"}

    # ----------------- Helpers -----------------
    def _load_json_files(self):
        base = os.path.dirname(__file__)
        with open(os.path.join(base, "available_params.json"), "r", encoding="utf-8") as f:
            params_json = json.load(f)
        with open(os.path.join(base, "type_plots.json"), "r", encoding="utf-8") as f:
            plots_json = json.load(f)
        return params_json, plots_json

    def _merge_plot_params(self, base_plot_params, plot_params_meta):
        merged = {}
        for key, meta in plot_params_meta.items():
            dv = meta.get("default", None)
            if isinstance(dv, str) and dv.startswith("Plot_params."):
                ref = dv.split(".")[-1]
                dv = base_plot_params.get(ref, "")
            merged[key] = dict(meta)
            merged[key]["default"] = dv
        return merged

    def _get_plot_class(self, ptype):
        return {
            "PSDPlot": PSDPlot,
            "LinearPlot": LinearPlot,
            "ViolinPlot": ViolinPlot,
            "ScatterPlot": ScatterPlot,
            "ERPPlot": ERPPlot
        }.get(ptype)

    def _create_available_plot_types(self, param_name, base_plot_params, plots_json):
        result = {}
        for ptype, pdata in plots_json.items():
            if param_name not in pdata.get("allowed_params", []):
                continue
            merged = self._merge_plot_params(base_plot_params, pdata.get("Plot_params", {}))
            plot_class = self._get_plot_class(ptype)
            if plot_class is None:
                continue
            result[ptype] = {
                "plot_class": plot_class,
                "plot_params_meta": merged,
                "plot_params_current": {k: v["default"] for k, v in merged.items()},
                "plot_obj": None,
                "param_widgets": {}
            }
        return result

    def _get_or_create_layout(self, placeholder):
        if placeholder is None:
            return None
        layout = placeholder.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(placeholder)
            layout.setContentsMargins(0, 0, 0, 0)
        return layout

    def _setup_scatter_x_options(self, tab, base_plot_params):
        if "ScatterPlot" not in tab._available_plot_types:
            return
        scatter_meta = tab._available_plot_types["ScatterPlot"]["plot_params_meta"]
        if "x_param" not in scatter_meta:
            return
        selected_params = list(self.view.main_module.controller.param_selection)
        x_options = []
        x_mapping = {}
        for p in selected_params:
            if p not in self.features_data:
                continue
            pname = self.features_data[p]["Param_name"]
            if pname not in self.plots_json.get("ScatterPlot", {}).get("allowed_params", []):
                continue
            bands = self.extract_bands_for_param(p)
            short_name = self.abbreviate_param_name(pname)
            for band in bands:
                label = f"{short_name} - {band.capitalize()}"
                value = f"{p}|{band}"
                x_options.append(label)
                x_mapping[label] = value
        scatter_meta["x_param"]["options"] = x_options
        scatter_meta["x_param"]["_mapping"] = x_mapping
        if x_options:
            scatter_meta["x_param"]["default"] = x_options[0]

    # ----------------- Main flow -----------------
    def create_tabs(self):
        """ Create the tabs """
        if self.view.main_module.is_erp:
            from plots_stats.param_selection.flow import filter_files_by_selection
            self.view.main_module.controller.filtered_files = filter_files_by_selection(self.view)
        selected_parameters = self.view.main_module.controller.param_selection
        if selected_parameters is None:
            return

        self.view.main_module.loading.show()
        self.view.main_module.loading.set_progress(0, self.view.main_module)

        try:
            param_iter = list(selected_parameters)
        except Exception:
            param_iter = [str(selected_parameters)]

        files = self.view.main_module.controller.filtered_files
        self.filtered_files = self.filter_recordings()
        self.available_bands = self.extract_unique_bands(files)
        self.group_colors = dict(self.view.main_module.controller.groups)

        tab_widget = self.view.tab_widget
        while tab_widget.count() > 0:
            tab_widget.removeTab(0)

        params_json, plots_json = self._load_json_files()
        self.plots_json = plots_json
        experiment_type = self.view.main_module.controller.experiment_type
        self.features_data = params_json.get(experiment_type, [])[0]

        total = max(len(param_iter), 1)
        self.view.main_module.loading.set_progress((1 / total) * 100, self.view.main_module)

        for idx, param in enumerate(param_iter):
            if param not in self.features_data:
                print(f"[WARN] Parameter '{param}' not found in available_params.json. Skipping.")
                continue

            param_name = self.features_data[param]["Param_name"]
            self.param_name_to_key = {v["Param_name"]: k for k, v in self.features_data.items()}
            base_plot_params = self.features_data[param]["Plot_params"]

            tab = self.load_ui(self.template_ui_path, parent=tab_widget)

            self.setup_channel_list(tab, param)
            self.setup_band_list(tab, param)
            if self.available_bands:
                self.on_band_selected(tab, param, self.available_bands[0])

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
            plot_obj = plot_class(ax, plot_info["plot_params_current"])
            plot_info["plot_obj"] = plot_obj
            tab._plot = plot_obj
            tab._figure = fig
            tab._canvas = canvas
            tab._plot_type = tab._current_plot_type
            tab._plot_params = plot_info["plot_params_meta"]
            tab._plot_params_current = plot_info["plot_params_current"]

            if layout is not None:
                layout.addWidget(canvas)

            # ScatterPlot options
            self._setup_scatter_x_options(tab, base_plot_params)

            controls_widget = tab.findChild(QtWidgets.QWidget, "controlWidget")
            build_dynamic_controls(self, controls_widget, tab._available_plot_types[tab._current_plot_type]["plot_params_meta"], tab)

            tab._force_autolimits = True
            self.update_plot(tab)

            prev_btn = tab.findChild(QtWidgets.QPushButton, "prevButton")
            prev_btn.clicked.connect(self.prev_tab)
            next_btn = tab.findChild(QtWidgets.QPushButton, "nextButton")
            next_btn.clicked.connect(self.next_tab)
            export_btn = tab.findChild(QtWidgets.QPushButton, "exportButton")
            export_btn.clicked.connect(lambda checked, t=tab: self.export_figure(t))
            update_btn = tab.findChild(QtWidgets.QPushButton, "updateButton")
            update_btn.clicked.connect(lambda checked, t=tab: self.update_plot(t))

            self.view.add_tab(tab, str(param_name))
            self._tabs_created = True

            progress = ((idx + 1) / total) * 100
            self.view.main_module.loading.set_progress(progress, self.view.main_module)

        self.view.main_module.loading.finish()

    def load_ui(self, path, parent=None):
        """Load the tab_template UI from the given path."""
        form_class, base_class = loadUiType(path)
        widget = base_class(parent) if parent is not None else base_class()
        ui = form_class()
        ui.setupUi(widget)
        return widget

    def setup_channel_list(self, tab, param):
        """ Config the channel list """
        list_widget = tab.findChild(QtWidgets.QListWidget, "channelListWidget")
        channels = self.view.main_module.controller.config_config.get("channel_names", [])

        if not channels:
            print('Channels not found')
            return

        list_widget.clear()
        for ch in channels:
            list_widget.addItem(QtWidgets.QListWidgetItem(ch))

        if list_widget.count() > 0:
            list_widget.setCurrentRow(0)

        tab._selected_channels = {param: 0}
        self.on_channels_selected(tab, param)
        list_widget.itemSelectionChanged.connect(lambda: self.on_channels_selected(tab, param))

    def on_channels_selected(self, tab, param):
        """Read the selected channels and store its indices"""
        list_widget = tab.findChild(QtWidgets.QListWidget, "channelListWidget")
        selected_indexes = [list_widget.row(item) for item in list_widget.selectedItems()]
        tab._selected_channels[param] = selected_indexes
        tab._force_autolimits = True
        print(f"Selected channel indices for param '{param}': {selected_indexes}")

    def extract_unique_bands(self, param_list):
        """ Extract unique bands from all files"""
        bands = set()
        for p in param_list:
            match = re.search(r"_band-([a-zA-Z0-9]+)", p)
            if match:
                bands.add(match.group(1))
        return sorted(list(bands))

    def setup_band_list(self, tab, param):
        """Configure the band list"""
        combo_box = tab.findChild(QtWidgets.QComboBox, "bandscomboBox")
        combo_box.clear()
        for b in self.available_bands:
            combo_box.addItem(b)
        if combo_box.count() > 0:
            combo_box.setCurrentIndex(0)
        combo_box.currentTextChanged.connect(lambda band: self.on_band_selected(tab, param, band))
        if combo_box.count() > 0:
            self.on_band_selected(tab, param, combo_box.currentText())

    def filter_recordings_by_band(self, param, selected_band):
        """
        Create a dic with filtered files for the corresponding param and the selected band.
        """
        param_files_dict = self.filtered_files.get(param, {})
        filtered_files_bands = {}
        for group, file_list in param_files_dict.items():
            if self.view.main_module.is_erp:
                valid = [f for f in file_list if f"_band-{selected_band}" in f and "segmented" in f]
            else:
                valid = [f for f in file_list if f"_band-{selected_band}" in f and f"_param-{param}" in f]
            if valid:
                filtered_files_bands.setdefault(param, {})[group] = valid
        return filtered_files_bands

    def on_band_selected(self, tab, param, selected_band):
        filtered_files_bands = self.filter_recordings_by_band(param, selected_band)
        tab._filtered_files_bands = filtered_files_bands
        tab._filtered_files_y = filtered_files_bands
        tab._current_band_y = selected_band
        tab._current_band = selected_band
        tab._force_autolimits = True

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
                sub = item.layout()
                if sub is not None:
                    self._clear_layout(sub)

    def update_plot(self, tab):
        """
        Generic update method for plots. Delegates to the specific plot class.
        """
        try:
            if not hasattr(tab, "_current_plot_type") or not hasattr(tab, "_plot"):
                print("[WARN] Tab not ready for plotting.")
                return

            plot_type = tab._current_plot_type
            plot_obj = tab._plot
            is_scatter = plot_type == "ScatterPlot"
            is_simple = plot_type in self.simple_plots

            if hasattr(tab, "_param_widgets"):
                tab._plot_params_current = {
                    key: self._get_widget_value(ptype, widget)
                    for key, (ptype, widget) in tab._param_widgets.items()
                }

            param_y = list(tab._selected_channels.keys())[0]
            sel = tab._selected_channels.get(param_y, 0)
            selected_channels = sel if isinstance(sel, (list, tuple, set)) else [int(sel)]

            if is_simple:
                filtered = tab._filtered_files_bands.get(param_y, {})
                tab._data_mode = self.detect_data_mode(filtered, selected_channels)
                self.filter_plot_types_by_mode(tab, self.plots_json)
                plot_obj.plot_params = tab._plot_params_current
                if plot_type == "ERPPlot":
                    window = getattr(self.view.main_module.controller, "window", None)
                    if window is not None:
                        plot_obj.plot_params["_time_window"] = window

                if tab._force_autolimits:
                    tab._plot_params_current["ylim"] = [None, None]

                ylim_user = tab._plot_params_current.get("ylim", None)
                user_defined_ylim = (
                    not tab._force_autolimits and
                    isinstance(ylim_user, (list, tuple)) and
                    len(ylim_user) == 2 and
                    any(v is not None for v in ylim_user)
                )

                plot_obj.load_data(filtered, selected_channels)
                plot_obj.draw(colors=self.group_colors)

                if not user_defined_ylim:
                    self._sync_widgets_with_plot(tab, plot_obj)

                tab._force_autolimits = False

            elif is_scatter:
                scatter_meta = tab._available_plot_types["ScatterPlot"]["plot_params_meta"]
                x_mapping = scatter_meta["x_param"].get("_mapping", {})

                x_label = tab._plot_params_current.get("x_param")
                encoded = x_mapping.get(x_label)
                if not encoded:
                    print(f"[WARN] Invalid x_param selection: {x_label}")
                    return

                param_x, band_x = encoded.split("|")

                param_y_name = f"{self.features_data[param_y]['Param_name']} ({tab._current_band_y})"
                param_x_name = f"{self.features_data[param_x]['Param_name']} ({band_x})"

                tab._plot_params_current.update({
                    "x_label": param_x_name,
                    "y_label": param_y_name,
                    "title": f"{param_y_name} vs {param_x_name}"
                })

                for key in ("x_label", "y_label", "title"):
                    if key in tab._param_widgets:
                        ptype, widget = tab._param_widgets[key]
                        if ptype in ("text", "range", "number"):
                            widget.setText(str(tab._plot_params_current[key]))

                filtered_y = tab._filtered_files_y.get(param_y, {})
                filtered_x_all = self.filter_recordings_by_band(param_x, band_x)
                filtered_x = filtered_x_all.get(param_x, {})

                new_x_param = tab._plot_params_current.get("x_param")
                if new_x_param != getattr(tab, "_last_x_param", None):
                    tab._force_autolimits = True
                    tab._last_x_param = new_x_param

                plot_obj.plot_params = tab._plot_params_current
                if tab._force_autolimits:
                    tab._plot_params_current["xlim"] = [None, None]
                    tab._plot_params_current["ylim"] = [None, None]

                plot_obj.load_data(filtered_y, filtered_x, selected_channels)
                plot_obj.draw(colors=self.group_colors)

                self._sync_widgets_with_plot(tab, plot_obj)
                tab._force_autolimits = False

            else:
                print(f"[WARN] Unsupported plot type: {plot_type}")

            if hasattr(tab, "_canvas"):
                tab._canvas.draw()

        except Exception as e:
            print(f"[ERROR] Exception in update_plot: {e}")
            if hasattr(tab, "_plot"):
                tab._plot.clear()
            if hasattr(tab, "_canvas"):
                tab._canvas.draw()

    def _get_widget_value(self, ptype, widget):
        """Helper to extract a typed value from a widget."""
        import json
        if ptype in ("text", "range", "number"):
            text = widget.text().strip()
            try:
                return json.loads(text)
            except Exception:
                return text
        elif ptype == "bool":
            return widget.isChecked()
        elif ptype == "select":
            return widget.currentText()
        elif ptype == "color":
            return widget.text()
        elif ptype == "spin":
            return widget.value()
        elif ptype == "doublespin":
            return widget.value()
        return None

    def prev_tab(self):
        """Go back to the previous tab."""
        current = self.view.tab_widget.currentIndex()
        if current > 0:
            self.view.tab_widget.setCurrentIndex(current - 1)

    def next_tab(self):
        """Go forward to the next tab."""
        current = self.view.tab_widget.currentIndex()
        if current < self.view.tab_widget.count() - 1:
            self.view.tab_widget.setCurrentIndex(current + 1)

    def export_figure(self, tab):
        fig = getattr(tab, "_figure", None)
        plot_type = getattr(tab, "_plot_type", "figure")
        export_figure_generic(view=self.view, fig=fig, suggested_name=f"{plot_type}", warn_if_none=False)

    def filter_recordings(self):
        files = self.view.main_module.controller.filtered_files
        parameters = getattr(self.view.main_module.controller, "param_selection", None)
        separated_files_param = {}
        for param in parameters:
            for file in files:
                if param in file:
                    separated_files_param.setdefault(param, []).append(file)

        groups = self.view.main_module.controller.group_assignment
        separated_files = {}
        for key in separated_files_param.keys():
            separated_files[key] = {group: [] for group in groups}
            for file in separated_files_param[key]:
                for group in groups:
                    pass_group = False
                    for element in groups[group]:
                        parts = element.split('_')
                        all_present = True
                        for part in parts:
                            if part not in file:
                                all_present = False
                                break
                        if not all_present:
                            continue
                        else:
                            pass_group = True
                            break
                    if not pass_group:
                        continue
                    else:
                        separated_files.setdefault(key, {}).setdefault(group, []).append(file)
                        break
        return separated_files

    def _sync_widgets_with_plot(self, tab, plot_obj):
        """
        Update widget values using real plot data only when user has not defined them.
        """
        limits = plot_obj.get_last_limits()
        if not limits:
            return

        for key, value in limits.items():
            if key not in tab._param_widgets:
                continue

            current = tab._plot_params_current.get(key, None)
            if current is not None and isinstance(current, (list, tuple)) and len(current) == 2 and any(v is not None for v in current):
                continue

            ptype, widget = tab._param_widgets[key]
            if ptype == "range" and isinstance(value, (list, tuple)) and len(value) == 2:
                lo = round(value[0], 2)
                hi = round(value[1], 2)
                text = f"[{lo}, {hi}]"
                widget.setText(text)

    def on_plot_type_changed(self, tab, container_widget, plot_type):
        """
        Called when the plot type combo changes.
        Rebuilds widgets and updates the plot automatically.
        """
        if plot_type not in tab._available_plot_types:
            return

        tab._current_plot_type = plot_type
        plot_info = tab._available_plot_types[plot_type]

        if plot_info["plot_obj"] is None:
            ax = tab._figure.axes[0]
            ax.cla()
            ax.figure.canvas.draw_idle()
            plot_info["plot_obj"] = plot_info["plot_class"](ax, plot_info["plot_params_current"])

        tab._plot = plot_info["plot_obj"]
        tab._plot_type = plot_type
        tab._plot_params_current = {k: v["default"] for k, v in plot_info["plot_params_meta"].items()}
        plot_info["plot_params_current"] = tab._plot_params_current

        layout = container_widget.layout()
        if layout is not None:
            self._clear_layout(layout)

        build_dynamic_controls(self, container_widget, plot_info["plot_params_meta"], tab)

        tab._force_autolimits = True
        self.update_plot(tab)

    def filter_plot_types_by_mode(self, tab, plots_json):
        """
        Remove plot types that are not compatible with current data mode.
        """
        mode = getattr(tab, "_data_mode", None)
        if mode is None:
            return

        to_remove = []
        for ptype, pdata in plots_json.items():
            required = pdata.get("requires_mode", None)
            if required is None:
                continue
            if isinstance(required, str):
                required = [required]
            if mode not in required and ptype in tab._available_plot_types:
                to_remove.append(ptype)

        for ptype in to_remove:
            del tab._available_plot_types[ptype]

        if tab._current_plot_type not in tab._available_plot_types:
            if tab._available_plot_types:
                tab._current_plot_type = list(tab._available_plot_types.keys())[0]
                tab._plot = tab._available_plot_types[tab._current_plot_type]["plot_obj"]

    def detect_data_mode(self, filtered_files, selected_channels):
        """
        Detects whether data is vector or time_series using the first valid file.
        """
        import scipy.io
        import numpy as np

        for group, files in filtered_files.items():
            for filepath in files:
                try:
                    mat = scipy.io.loadmat(filepath, squeeze_me=True, struct_as_record=False)
                except Exception:
                    continue

                data = None
                for key in ("param", "vector", "values", "valores"):
                    if key in mat:
                        data = np.asarray(mat[key]).squeeze()
                        break

                if data is None:
                    for key, val in mat.items():
                        if isinstance(val, np.ndarray):
                            data = val
                            break

                if data is None:
                    continue

                data = np.asarray(data)
                if data.ndim == 1 or (data.ndim == 2 and data.shape[0] == 1):
                    return "vector"
                if data.ndim == 2:
                    return "time_series"

        return None

    def extract_bands_for_param(self, param_key):
        """
        Returns sorted list of bands available for a given param key.
        """
        bands = set()
        param_files = self.filtered_files.get(param_key, {})
        for group_files in param_files.values():
            for f in group_files:
                match = re.search(r"_band-([a-zA-Z0-9]+)", f)
                if match:
                    bands.add(match.group(1))
        return sorted(bands)

    def abbreviate_param_name(self, name: str) -> str:
        """
        If name has 2 or more words → initials (Relative Power -> RP)
        If only 1 word → keep it (Complexity)
        """
        parts = name.split()
        if len(parts) >= 2:
            return "".join(word[0].upper() for word in parts)
        return name
