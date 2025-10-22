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
        # Extract available bands
        self.available_bands = self.extract_unique_bands(files)

        tab_widget = self.view.tab_widget
        while tab_widget.count() > 0:
            tab_widget.removeTab(0)

        # Load params_plots.json and plot_plots to obtain plot types and parameters for each param
        params_json_path = os.path.join(os.path.dirname(__file__), "params_plots_2.json")
        plots_json_path = os.path.join(os.path.dirname(__file__), "plot_plots.json")
        with open(params_json_path, "r", encoding="utf-8") as f:
            params_json = json.load(f)
        with open(plots_json_path, "r", encoding="utf-8") as f:
            plots_json = json.load(f)

        experiment_type = self.view.main_module.controller.experiment_type
        features_data  = params_json.get(experiment_type, [])[0]

        # For each selected param, we inset one tab in de TabWidget
        for param in param_iter:

            if param not in features_data:
                print(f"[WARN] Parameter '{param}' not found in params_plots.json. Skipping.")
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

            # Create de FigureCanvas in the placeholder to inser the plot
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

            if controls_widget:
                # ✅ Asegurar que esté dentro del controlPanel
                control_panel = tab.findChild(QtWidgets.QFrame, "controlPanel")
                if control_panel is not None:
                    # Si el panel no tiene layout, se lo creamos
                    if control_panel.layout() is None:
                        panel_layout = QtWidgets.QVBoxLayout(control_panel)
                        panel_layout.setContentsMargins(0, 0, 0, 0)
                        panel_layout.setSpacing(5)
                        control_panel.setLayout(panel_layout)
                    else:
                        panel_layout = control_panel.layout()

                    # ✅ Si el TypePlotWidget no está ya en el layout del panel, lo insertamos
                    if control_panel.layout().indexOf(controls_widget) == -1:
                        panel_layout.addWidget(controls_widget)

                    # ✅ Forzar tamaño expandible
                    controls_widget.setSizePolicy(
                        QtWidgets.QSizePolicy.Expanding,
                        QtWidgets.QSizePolicy.Expanding
                    )

                # Ahora sí construimos los controles
                self._build_dynamic_controls(controls_widget, merged_params, tab)

            # Connect buttons
            prev_btn = tab.findChild(QtWidgets.QPushButton, "prevButton")
            next_btn = tab.findChild(QtWidgets.QPushButton, "nextButton")
            export_btn = tab.findChild(QtWidgets.QPushButton, "exportButton")

            if prev_btn:
                prev_btn.clicked.connect(self.prev_tab)
            if next_btn:
                next_btn.clicked.connect(self.next_tab)
            if export_btn:
                export_btn.clicked.connect(lambda checked, t=tab: self.export_figure(t))

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

        # Connect --> TO DO (que promedie y luego llame a update_plot)
        list_widget.currentTextChanged.connect(lambda ch: self.on_channel_selected(param, ch))

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

        list_widget.currentTextChanged.connect(lambda band: self.on_band_selected(param, band))

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
        Crea controles dinámicos para editar los parámetros del plot de forma genérica.
        Añade al inicio una etiqueta 'Plot type: <tipo>'.
        """
        if not isinstance(container_widget, QtWidgets.QWidget):
            return

        # --- 🔧 Limpiar layout previo si existe ---
        old_layout = container_widget.layout()
        if old_layout is not None:
            try:
                self._clear_layout(old_layout)
                # Desconectar el layout viejo del widget sin destruirlo prematuramente
                dummy = QtWidgets.QWidget()
                dummy.setLayout(old_layout)
            except RuntimeError:
                # El layout ya fue destruido por Qt, ignoramos
                pass

        # --- 🔧 Crear un nuevo QFormLayout ---
        form = QtWidgets.QFormLayout()
        form.setVerticalSpacing(8)
        form.setHorizontalSpacing(12)
        form.setContentsMargins(6, 6, 6, 6)
        container_widget.setLayout(form)

        # --- 1️⃣ Etiqueta inicial con tipo de plot ---
        plot_type_label = QtWidgets.QLabel(f"Plot type: {getattr(tab, '_plot_type', 'Unknown')}")
        font = plot_type_label.font()
        font.setBold(True)
        plot_type_label.setFont(font)
        form.addRow(plot_type_label)

        # --- 2️⃣ Crear dinámicamente cada parámetro ---
        for key, meta in plot_params.items():
            if isinstance(meta, dict) and any(k in meta for k in ("type", "default", "label")):
                param_type = meta.get("type", "text")
                label_text = meta.get("label", key)
                default_value = meta.get("default", "")
            else:
                param_type = "text"
                label_text = key
                default_value = meta

            widget = None

            # TEXT / RANGE
            if param_type in ("text", "range"):
                widget = QtWidgets.QLineEdit()
                if isinstance(default_value, (list, tuple, dict)):
                    widget.setText(json.dumps(default_value))
                else:
                    widget.setText(str(default_value))
                widget.textChanged.connect(lambda value, k=key, t=tab: self._update_plot_param(t, k, value))

            # BOOL
            elif param_type == "bool":
                widget = QtWidgets.QCheckBox()
                dv = bool(default_value) if not isinstance(default_value, str) else default_value.lower() in ("1",
                                                                                                              "true",
                                                                                                              "yes")
                widget.setChecked(dv)
                widget.stateChanged.connect(lambda state, k=key, t=tab: self._update_plot_param(t, k, bool(state)))

            # SELECT
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
                widget.currentTextChanged.connect(lambda value, k=key, t=tab: self._update_plot_param(t, k, value))

            # Fallback
            else:
                widget = QtWidgets.QLineEdit()
                if isinstance(default_value, (list, tuple, dict)):
                    widget.setText(json.dumps(default_value))
                else:
                    widget.setText(str(default_value))
                widget.textChanged.connect(lambda value, k=key, t=tab: self._update_plot_param(t, k, value))

            if widget is not None:
                form.addRow(QtWidgets.QLabel(label_text), widget)

        # --- 🔧 Ajustar políticas de tamaño y refrescar ---
        container_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Preferred
        )
        container_widget.setMinimumHeight(250)

        form.invalidate()
        form.update()
        container_widget.updateGeometry()
        container_widget.adjustSize()

        # 🔧 Forzar recalculado hacia arriba
        parent = container_widget.parentWidget()
        while parent is not None:
            parent.adjustSize()
            parent.updateGeometry()
            parent = parent.parentWidget()

        QtWidgets.QApplication.processEvents()

        # --- DEBUG visual opcional ---
        # container_widget.setStyleSheet("background-color: rgba(0,255,0,40); border: 1px dashed green;")
        # for i in range(form.rowCount()):
        #     item = form.itemAt(i, QtWidgets.QFormLayout.FieldRole)
        #     if item and item.widget():
        #         item.widget().setStyleSheet("background-color: rgba(255,0,0,40); border: 1px solid red;")

        print(f"[DEBUG] Created {form.rowCount()} dynamic rows in {tab._plot_type}")
        for i in range(form.rowCount()):
            label_item = form.itemAt(i, QtWidgets.QFormLayout.LabelRole)
            field_item = form.itemAt(i, QtWidgets.QFormLayout.FieldRole)
            label_text = label_item.widget().text() if label_item and label_item.widget() else "None"
            field_type = type(field_item.widget()).__name__ if field_item and field_item.widget() else "None"
            print(f"   Row {i}: label={label_text}, field={field_type}")

    def _update_plot_param(self, tab, key, value):
        """Actualiza un parámetro del plot sin lógica específica."""
        if not hasattr(tab, "_plot") or not hasattr(tab, "_plot_params_current"):
            return

        params = tab._plot_params_current

        # Si value ya es bool (por checkbox) lo mantenemos; si es otro tipo intentamos parsear JSON
        parsed_value = value
        if not isinstance(value, bool):
            # value puede venir como int (estado), str, etc.
            try:
                # si es cadena con JSON -> parsear
                if isinstance(value, str):
                    parsed_value = json.loads(value)
                else:
                    parsed_value = value
            except Exception:
                parsed_value = value

        params[key] = parsed_value

        # Actualizamos los parámetros del plot
        plot_obj = tab._plot
        if hasattr(plot_obj, "plot_params"):
            plot_obj.plot_params.update(params)

        # Redibujamos si hay datos cargados
        if getattr(plot_obj, "_freqs", None) is not None and getattr(plot_obj, "_psd", None) is not None:
            try:
                plot_obj.update(plot_obj._freqs, plot_obj._psd)
                tab._canvas.draw()
            except Exception:
                # no queremos romper la UI si update falla
                pass

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