from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import (QFileDialog, QDialog)

from PySide6.QtUiTools import loadUiType
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from plots_stats.plot_panel.plot_classes import PSDPlot, TopographicPlotWrapper
from plots_stats.plot_panel.export_dialog import ExportDialog
from functools import partial
import re, os, json


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

        selected_parameters = getattr(self.view.main_module.controller, "params", None)
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
        filtered_files = self.filter_recordings()
        # Extract available bands
        self.available_bands = self.extract_unique_bands(files)

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
            # TODO: TANTOS PLOTS COMO GROUPS
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
            # TODO: Param name + group name
            title_label = tab.findChild(QtWidgets.QLabel, "titleLabel")
            if title_label:
                title_label.setText(param_name)

            # Create plot object based on plot_type
            tab._plot_type = plot_type
            if plot_type == "PSDPlot":
                plot_obj = PSDPlot(ax, {k: v["default"] for k, v in merged_params.items()})
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
        if not isinstance(container_widget, QtWidgets.QWidget):
            return

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
        scroll_area.setStyleSheet("""
                QScrollArea {
                    border: none;
                    background-color: #222;
                }
                QWidget {
                    background-color: transparent;
                }
            """)

        scroll_content = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(10, 10, 10, 10)

        # Title label
        plot_type_label = QtWidgets.QLabel(f"Plot type: {getattr(tab, '_plot_type', 'Unknown')}")
        plot_type_label.setAlignment(QtCore.Qt.AlignCenter)
        plot_type_label.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #6a0dad, stop:1 #ec407a);
                color: white;
                padding: 6px 12px;
                font-weight: 700;
                font-size: 9pt;
                border-radius: 6px;
            """)
        scroll_layout.addWidget(plot_type_label)

        tab._param_widgets = {} # Store references to created widgets

        # Loop over plot_params to create specific controls. Controls are created based on the 'type' metadata. For
        # example, type 'text' creates a QLineEdit, type 'bool' creates a QCheckBox, type 'select' creates a QComboBox, etc.
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
            card.setStyleSheet("""
                        QFrame {
                            background-color: transparent;
                            border-radius: 8px;
                            padding: 8px;
                        }
                    """)
            card_layout = QtWidgets.QVBoxLayout(card)
            card_layout.setSpacing(6)

            # Plot parameter subtitle
            title = QtWidgets.QLabel(label_text)
            title.setStyleSheet("font-weight:600; color:white; font-size:9pt; background-color: #C53189;")
            card_layout.addWidget(title)

            # Create the corresponding widget
            widget = None
            #If the param type is text or range, create a QLineEdit
            if param_type in ("text", "range", "number"):
                widget = QtWidgets.QLineEdit()
                if isinstance(default_value, (list, tuple, dict)):
                    widget.setText(json.dumps(default_value))
                else:
                    widget.setText(str(default_value))
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
                widget.setStyleSheet("""
                                QComboBox {
                                    background-color:#DCDCDC;
                                    color:black;
                                    border-radius:4px;
                                    padding:4px;
                                }
                            """)

            if widget is not None:
                widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
                card_layout.addWidget(widget)
                tab._param_widgets[key] = (param_type, widget)

            scroll_layout.addWidget(card)

        scroll_content.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        scroll_content.adjustSize()

        scroll_area.setWidget(scroll_content)
        scroll_area.setMinimumHeight(300)

        # Place scroll_area into the container widget's layout (replace existing layout)
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)
        container_widget.setLayout(main_layout)

        # Adjust sizes
        container_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        container_widget.setMinimumHeight(250)
        container_widget.updateGeometry()
        # container_widget.adjustSize()
        # QtWidgets.QApplication.processEvents()

        # print("TypePlotWidget height:", typePlotWidget.height())
        # print("ScrollArea height:", typePlotWidget.findChild(QtWidgets.QScrollArea).height())

    def update_plot(self, tab):
        """
        Read actual values from dynamic controls and update the plot.
        Only called when pressing the 'Update' button.
        """
        # TODO: MODIFICAR PARA QUE FUNCIONE CON TODOS LOS TIPOS DE PLOT Y LO QUE QUIERO YO
        if not hasattr(tab, "_plot") or not hasattr(tab, "_param_widgets"):
            print("[WARN] update_plot called but tab has no plot or param widgets.")
            return

        params = {}
        for key, (ptype, widget) in tab._param_widgets.items():
            if ptype in ("text", "range", "number"):
                txt = widget.text()
                # intentar parsear JSON o número
                try:
                    params[key] = json.loads(txt)
                except Exception:
                    params[key] = txt

            elif ptype == "bool":
                params[key] = widget.isChecked()

            elif ptype == "select":
                params[key] = widget.currentText()

            else:
                params[key] = str(widget.text())

        # Actualizamos los parámetros actuales
        tab._plot_params_current.update(params)

        # Actualizamos el plot_params del objeto gráfico
        plot_obj = tab._plot
        if hasattr(plot_obj, "plot_params"):
            plot_obj.plot_params.update(tab._plot_params_current)

        # Redibujar solo si hay datos cargados
        if getattr(plot_obj, "_freqs", None) is not None and getattr(plot_obj, "_psd", None) is not None:
            try:
                plot_obj.update(plot_obj._freqs, plot_obj._psd)
                tab._canvas.draw()
                print("[INFO] Plot updated with new parameters.")
            except Exception as e:
                print(f"[ERROR] Failed to update plot: {e}")

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
