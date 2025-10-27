from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import (QFileDialog, QDialog)

from PySide6.QtUiTools import loadUiType
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
# from plots_stats.plot_panel.plot_classes import PSDPlot, TopographicPlotWrapper
from plots_stats.plot_panel.plot_classes.base_plot  import BasePlot
from plots_stats.plot_panel.plot_classes.psd_plot import PSDPlot
from plots_stats.plot_panel.plot_classes.linear_plot import LinearPlot
from plots_stats.plot_panel.export_dialog import ExportDialog
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

    def create_tabs(self):
        """ Create the tabs """
        if self._tabs_created: # create tabs only once
            return

        selected_parameters = self.view.main_module.controller.param_selection
        if selected_parameters is None:
            return

        # Loading screen
        self.view.main_module.loading.show()
        self.view.main_module.loading.set_progress(0, self.view.main_module)

        try:
            param_iter = list(selected_parameters)
        except Exception:
            param_iter = [str(selected_parameters)]

        # Obtain paths of filtered files:
        files = self.view.main_module.controller.filtered_files
        self.filtered_files = self.filter_recordings()

        # Extract available bands
        self.available_bands = self.extract_unique_bands(files)

        # Extract group colors
        self.group_colors = list(self.view.main_module.controller.groups.values())

        tab_widget = self.view.tab_widget
        while tab_widget.count() > 0:
            tab_widget.removeTab(0)

        # Load available_params.json and type_plots.json to obtain the available plot for each param with its default params
        params_json_path = os.path.join(os.path.dirname(__file__), "available_params.json")
        plots_json_path = os.path.join(os.path.dirname(__file__), "type_plots.json")
        with open(params_json_path, "r", encoding="utf-8") as f:
            params_json = json.load(f)
        with open(plots_json_path, "r", encoding="utf-8") as f:
            plots_json = json.load(f)

        experiment_type = self.view.main_module.controller.experiment_type
        features_data  = params_json.get(experiment_type, [])[0]

        # For each selected param, we inset one tab in de TabWidget
        for param in param_iter:

            if param not in features_data:
                print(f"[WARN] Parameter '{param}' not found in available_params.json. Skipping.")
                continue

            param_name = features_data[param]["Param_name"]
            base_plot_params = features_data[param]["Plot_params"]

            # Find the associate plot type
            plot_type = None
            for ptype, pdata in plots_json.items():
                allowed = pdata["allowed_params"]
                if param_name in allowed:
                    plot_type = ptype
                    plot_type_data = pdata
                    break
            if not plot_type:
                print(f"[WARN] No plot type found for '{param}' in plot_plots.json")
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
            self.setup_channel_list(tab, param)
            self.setup_band_list(tab, param)

            # Create de FigureCanvas in the placeholder to insert the plot:
            placeholder = tab.findChild(QtWidgets.QWidget, "plotPlaceholder")
            if placeholder is None:
                layout = None
            else:
                layout = QtWidgets.QVBoxLayout(placeholder)
                layout.setContentsMargins(0, 0, 0, 0)
                layout = placeholder.layout()

            # Create plot object and store it in the tab for future.
            fig = Figure(figsize=(5, 4))
            canvas = FigureCanvas(fig)
            ax = fig.add_subplot(111)

            # Modify the title with the param name
            title_label = tab.findChild(QtWidgets.QLabel, "titleLabel")
            if title_label:
                title_label.setText(param_name)

            # Create plot object based on plot_type
            tab._plot_type = plot_type
            if plot_type == "PSDPlot":
                plot_obj = PSDPlot(ax, {k: v["default"] for k, v in merged_params.items()})
            elif plot_type == "LinearPlot":
                plot_obj = LinearPlot(ax, {k: v["default"] for k, v in merged_params.items()})
            # elif plot_type == "TopographicPlot":
            #     plot_obj = TopographicPlotWrapper(ax, {}, merged_params)
            else:
                plot_obj = None

            # Asociate the plot objet to the tab
            if plot_obj:
                tab._plot = plot_obj
                tab._figure = fig
                tab._canvas = canvas
                tab._plot_type = plot_type
                tab._plot_params = merged_params
                tab._plot_params_current = {k: v["default"] for k, v in merged_params.items()}

                layout.addWidget(canvas)
                canvas.draw()

            # Insert canvas in the placeholder
            layout.addWidget(canvas)
            canvas.draw()

            # Create dynamic controls for plot parameters in the tab view
            controls_widget = tab.findChild(QtWidgets.QWidget, "TypePlotWidget")
            self._build_dynamic_controls(controls_widget, merged_params, tab)

            # Connect buttons
            prev_btn = tab.findChild(QtWidgets.QPushButton, "prevButton")
            prev_btn.clicked.connect(self.prev_tab)
            next_btn = tab.findChild(QtWidgets.QPushButton, "nextButton")
            next_btn.clicked.connect(self.next_tab)
            export_btn = tab.findChild(QtWidgets.QPushButton, "exportButton")
            export_btn.clicked.connect(lambda checked, t=tab: self.export_figure(t))
            update_btn = tab.findChild(QtWidgets.QPushButton, "updateButton")
            update_btn.clicked.connect(lambda checked, t=tab: self.update_plot(t))

            # Add widget to main TabWindget
            self.view.add_tab(tab, str(param_name))
            self._tabs_created = True

            # Update loading progress
            self.view.main_module.loading.set_progress(((param_iter.index(param) + 1) / len(param_iter)) * 100, self.view.main_module)

        # Finish loading
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

        # Add channels to list
        list_widget.clear()
        for ch in channels:
            item = QtWidgets.QListWidgetItem(ch)
            list_widget.addItem(item)

        # First channel by default
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
        list_widget = tab.findChild(QtWidgets.QListWidget, "bandsWidget")
        list_widget.clear()
        for b in self.available_bands:
            item = QtWidgets.QListWidgetItem(b)
            list_widget.addItem(item)

        if list_widget.count() > 0:
            list_widget.setCurrentRow(0)

        list_widget.currentTextChanged.connect(lambda band: self.on_band_selected(tab, param, band))

        # Initialize paths filtration with the default band
        if list_widget.count() > 0:
            default_band = list_widget.currentItem().text()
            self.on_band_selected(tab, param, default_band)

    def filter_recordings_by_band(self, param, selected_band):
        """
        Create a dic with filtered files for the corresponding param and the selected band.
        """
        filtered_files_bands = {}
        param_files_dict = self.filtered_files.get(param, {})

        for group, file_list in param_files_dict.items():
            band_param_files = [
                f for f in file_list
                if f"_band-{selected_band}" in f and f"_param-{param}" in f
            ]
            if band_param_files:
                filtered_files_bands.setdefault(param, {}).setdefault(group, []).extend(band_param_files)

        return filtered_files_bands

    def on_band_selected(self, tab, param, selected_band):
        filtered_files_bands = self.filter_recordings_by_band(param, selected_band)
        self.filtered_files_bands = filtered_files_bands
        tab._filtered_files_bands = filtered_files_bands
        print(tab._filtered_files_bands)

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

    def _build_dynamic_controls(self, container_widget, plot_params, tab):
        """
        Create dynamic controls to edit plot parameters generically.
        Adds at the top a label 'Plot type: <type>'.
        """

        # Clear old layout if exists to avoid errors
        old_layout = container_widget.layout()
        if old_layout is not None:
            try:
                self._clear_layout(old_layout)
                dummy = QtWidgets.QWidget()
                dummy.setLayout(old_layout)
            except RuntimeError:
                pass

        # Scoll area
        scroll_area = QtWidgets.QScrollArea(container_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""QScrollArea {border: none; background-color: #222;} 
        QWidget {background-color: transparent;}""")
        scroll_content = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(10, 10, 10, 10)

        # Title label
        plot_type_label = QtWidgets.QLabel(f"Plot type: {getattr(tab, '_plot_type', 'Unknown')}")
        plot_type_label.setAlignment(QtCore.Qt.AlignCenter)
        plot_type_label.setStyleSheet("""background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6a0dad, stop:1 #ec407a);
                color: white; padding: 6px 12px; font-weight: 700; font-size: 9pt; border-radius: 6px; """)
        scroll_layout.addWidget(plot_type_label)

        tab._param_widgets = {} # Store references to created widgets

        # Loop over plot_params to create specific controls. Controls are created based on the 'type' metadata.
        for key, meta in plot_params.items():
            # If meta is a dict with 'type', 'default', 'label' keys, use them; else assume text type with label=key and default=meta
            if isinstance(meta, dict) and any(k in meta for k in ("type", "default", "label")):
                param_type = meta.get("type", "text")
                label_text = meta.get("label", key)
                default_value = meta.get("default", "")
            else:
                param_type = "text"
                label_text = key
                default_value = meta

            # Card container
            card = QtWidgets.QFrame()
            card.setFrameShape(QtWidgets.QFrame.StyledPanel)
            card.setStyleSheet("""QFrame {background-color: transparent; border-radius: 8px; } """)
            card.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)

            card_layout = QtWidgets.QVBoxLayout(card)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(4)

            # Plot parameter subtitle
            title = QtWidgets.QLabel(label_text)
            title.setStyleSheet("font-weight:600; color:white; font-size:9pt; background-color: #C53189;")
            card_layout.addWidget(title)

            # Create the corresponding widget
            widget = None
            #If the param type is text or range, create a QLineEdit
            if param_type in ("text", "range", "number"):
                widget = QtWidgets.QLineEdit()
                if default_value is None and param_type == "range":
                    display_value = "[None, None]"
                elif default_value is None:
                    display_value = ""
                elif isinstance(default_value, (list, tuple, dict)):
                    display_value = json.dumps(default_value)
                else:
                    display_value = str(default_value)
                widget.setText(display_value)
                widget.setStyleSheet("background-color:#DCDCDC; color:black; border-radius:4px; padding:4px;")

            # If the param type is bool, create a QCheckBox
            elif param_type == "bool":
                widget = QtWidgets.QCheckBox()
                dv = bool(default_value) if not isinstance(default_value, str) else default_value.lower() in ("1","true","yes")
                widget.setChecked(dv)
                widget.setStyleSheet("color:white;")

            # If the param type is select, create a QComboBox
            elif param_type == "select":
                widget = QtWidgets.QComboBox()
                options = meta.get("options", []) if isinstance(meta, dict) else []
                for opt in options:
                    widget.addItem(str(opt))
                if default_value not in (None, "") and str(default_value) not in [str(o) for o in options]:
                    widget.addItem(str(default_value))
                if default_value is not None and default_value != "":
                    idx = widget.findText(str(default_value))
                    if idx >= 0:
                        widget.setCurrentIndex(idx)
                widget.setStyleSheet("""QComboBox {background-color:#DCDCDC; color:black; border-radius:4px; padding:4px;}""")

            # Add widget to card layout
            if widget is not None:
                widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
                card_layout.addWidget(widget)
                tab._param_widgets[key] = (param_type, widget)

            scroll_layout.addWidget(card)

        scroll_content.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        scroll_content.adjustSize()
        scroll_area.setWidget(scroll_content)

        # Place scroll_area into the container widget's layout (replace existing layout)
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)
        container_widget.setLayout(main_layout)

        # Adjust sizes of the container widget
        container_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        container_widget.setMinimumHeight(170)
        container_widget.updateGeometry()

    def update_plot(self, tab):
        """
        Generic update method for plots. Delegates to the specific plot class.
        """
        try:
            if not hasattr(tab, "_plot_type"):
                print("[WARN] Tab has no _plot_type.")
                return

            plot_type = tab._plot_type
            plot_obj = getattr(tab, "_plot", None)

            if plot_obj is None:
                print(f"[WARN] No plot object found for type {plot_type}.")
                return

            # Update plot params from widgets
            if hasattr(tab, "_param_widgets"):
                tab._plot_params_current = {
                    key: self._get_widget_value(ptype, widget)
                    for key, (ptype, widget) in tab._param_widgets.items()
                }

            # Delegate per-plot data loading
            if plot_type == "PSDPlot" or plot_type=='LinearPlot':
                if not hasattr(tab, "_selected_channels") or not tab._selected_channels:
                    print("[WARN] No selected channels found in tab.")
                    return

                param = list(tab._selected_channels.keys())[0]
                filtered = tab._filtered_files_bands.get(param, {})

                # --- Ensure selected_channels is always a list ---
                sel = tab._selected_channels.get(param, 0)
                if isinstance(sel, (int, float)):
                    selected_channels = [int(sel)]
                elif isinstance(sel, (list, tuple, set)):
                    selected_channels = list(sel)
                else:
                    selected_channels = [0]

                # --- Delegate to PSDPlot instance ---
                plot_obj.plot_params = tab._plot_params_current
                plot_obj.load_data(filtered, selected_channels)
                if plot_type == 'PSDPlot':
                    plot_obj.draw(colors = self.group_colors)
                elif plot_type == 'LinearPlot':
                    plot_obj.draw(colors = self.group_colors)

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
        """Export the figure from the given tab. Open a QFileDialog to choose the path and a dialog
        with saving options."""
        dlg = ExportDialog(self.view)
        if dlg.exec() != QDialog.Accepted:
            return
        vals = dlg.get_values()
        fmt = vals["format"]
        dpi = vals["dpi"]
        width_px = vals["width"]
        height_px = vals["height"]
        transparent = vals["transparent"]
        bg_color = vals["bg_color"]

        suggested_name = f"{tab.findChild(QtWidgets.QLabel, 'titleLabel').text()}.{fmt}"
        fname, _ = QFileDialog.getSaveFileName(self.view, "Save image", suggested_name,
                                              f"{fmt.upper()} (*.{fmt})")
        if not fname:
            return

        # Asjust figure size: matplotlib uses inches so we have to convert px to inches
        inches_width = width_px / dpi
        inches_height = height_px / dpi

        fig = getattr(tab, "_figure", None)
        if fig is None:
            return

        original_size = fig.get_size_inches()
        try:
            fig.set_size_inches(inches_width, inches_height)

            # Si no es transparente, usar el color de fondo elegido
            facecolor = "none" if transparent else bg_color
            fig.savefig(fname, dpi=dpi, transparent=transparent,
                        bbox_inches="tight", facecolor=facecolor)
        finally:
            # restore original sizer for avoid afecting the canvas visual representation in the widget
            fig.set_size_inches(original_size)

        QtWidgets.QMessageBox.information(self.view, "Export", f"Saved to:\n{fname}")

    def filter_recordings(self):
        files = self.view.main_module.controller.filtered_files

        parameters = getattr(self.view.main_module.controller, "params", None)
        separated_files_param = {}
        for param in parameters:
            for file in files:
                if param in file:
                    separated_files_param.setdefault(param, []).append(file)

        # Separate files by groups
        groups = self.view.main_module.controller.group_assignment
        separated_files = {}
        for key in separated_files_param.keys():
            for file in separated_files_param[key]:
                for group in groups:

                    # Group files based on group assignment
                    pass_group = False
                    for element in groups[group]:
                        # Split the element with '_'
                        parts = element.split('_')

                        # Check if all parts are present in the file name
                        all_present = True
                        for part in parts:
                            if part not in file:
                                all_present = False
                                break
                        # If not all present, skip to the next file
                        if not all_present:
                            continue
                        # If present, mark as passed and break the loop
                        else:
                            pass_group = True
                            break
                    # If no group matched, skip to the next file
                    if not pass_group:
                        continue
                    else:
                        separated_files.setdefault(key, {}).setdefault(group, []).append(file)
                        break
        return separated_files
