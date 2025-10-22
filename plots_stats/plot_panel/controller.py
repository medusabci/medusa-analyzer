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

        # Load params_plots.json to obtain plot types and parameters for each param
        json_path = os.path.join(os.path.dirname(__file__), "params_plots.json")
        with open(json_path, "r", encoding="utf-8") as f:
            params_json = json.load(f)

        experiment_type = self.view.main_module.controller.experiment_type
        features_plot_info = params_json.get(experiment_type, {}) # TODO: leer derl experiment ID

        # For each selected param, we inset one tab in de TabWidget
        for param in param_iter:
            tab = self.load_ui(self.template_ui_path, parent=tab_widget)

            self.setup_channel_list(tab, param)
            self.setup_band_list(tab, param)

            # Create de FigureCanvas in the placeholder to inser the plot
            placeholder = tab.findChild(QtWidgets.QWidget, "plotPlaceholder")
            if placeholder is None:
                layout = None
            else:
                if placeholder.layout() is None:
                    layout = QtWidgets.QVBoxLayout(placeholder)
                    layout.setContentsMargins(0, 0, 0, 0)
                else:
                    layout = placeholder.layout()

            if layout is not None:
                # Create plot object and store it in the tab for future.
                fig = Figure(figsize=(5, 4))
                canvas = FigureCanvas(fig)
                ax = fig.add_subplot(111)

                # Extract plot type and parameters from params_json
                feature_data = features_plot_info[0].get(param, {})
                if not feature_data:
                    print(f"[WARN] Configuration not found for '{param}'. Skipping plot.")
                    continue

                param_name = feature_data["Param_name"]
                plot_type = feature_data["Type_of_plot"]
                plot_params_from_json = feature_data.get("Plot_params", {}) or {}
                default_params = {
                    k: (v["default"] if isinstance(v, dict) and "default" in v else v)
                    for k, v in plot_params_from_json.items()
                }

                # Modify the title with the param name
                title_label = tab.findChild(QtWidgets.QLabel, "titleLabel")
                if title_label:
                    title_label.setText(param_name)  # TODO: poner un nombre más amigable

                # Create the plot object depending on the type
                if plot_type == "PSDPlot":
                    plot_obj = PSDPlot(ax, default_params)
                elif plot_type == "TopographicPlot":
                    plot_obj = None
                    # plot_obj = TopographicPlotWrapper(ax, channel_set, plot_params_from_json)
                    pass
                else: # Unknown plot type
                    print(f"[WARN] Unknown plot type '{plot_type}' for param '{param}'. Skipping plot.")
                    continue

                # Asociate the plot objet to the tab
                tab._plot = plot_obj
                tab._figure = fig
                tab._canvas = canvas
                tab._plot_type = plot_type
                tab._plot_params = plot_params_from_json
                tab._plot_params_current = dict(default_params)

                # Insert canvas in the placeholder
                fig.tight_layout()
                layout.addWidget(canvas)
                canvas.draw()

                # Create dynamic controls for plot parameters in the tab view
                controls_widget = tab.findChild(QtWidgets.QWidget, "TypePlotWidget")
                if controls_widget:
                    self._build_dynamic_controls(controls_widget, plot_params_from_json, tab)

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
        container_widget: QWidget (no layout). El método creará/establecerá un QFormLayout en él.
        plot_params: dict con metadatos por parámetro.
        """
        if not isinstance(container_widget, QtWidgets.QWidget):
            # defensiva: si por cualquier razón llegó otra cosa, intentamos extraer widget
            return

        # Si el widget ya tiene un layout, lo limpiamos y lo sustituimos por QFormLayout
        existing = container_widget.layout()
        if existing is not None:
            self._clear_layout(existing)
        form = QtWidgets.QFormLayout(container_widget)
        form.setContentsMargins(0, 0, 0, 0)

        for key, meta in plot_params.items():
            # --- 1️⃣ Detectar tipo de parámetro ---
            if isinstance(meta, dict) and any(k in meta for k in ("type", "default", "label")):
                param_type = meta.get("type", "text")
                label_text = meta.get("label", key)
                default_value = meta.get("default", "")
            else:
                # Valor simple → tratamos como texto editable
                param_type = "text"
                label_text = key
                default_value = meta

            # --- 2️⃣ Crear el widget según el tipo ---
            widget = None

            # TEXT / RANGE (edición libre mediante QLineEdit)
            if param_type in ("text", "range"):
                widget = QtWidgets.QLineEdit()
                if isinstance(default_value, (list, tuple, dict)):
                    widget.setText(json.dumps(default_value))
                else:
                    widget.setText(str(default_value))

                # conectar con update, hacemos parseo JSON dentro de _update_plot_param
                widget.textChanged.connect(lambda value, k=key, t=tab: self._update_plot_param(t, k, value))

            # BOOL → QCheckBox
            elif param_type == "bool":
                widget = QtWidgets.QCheckBox()
                # set default state (handle strings like "true"/"false" or bool)
                if isinstance(default_value, str):
                    dv = default_value.lower() in ("1", "true", "yes")
                else:
                    dv = bool(default_value)
                widget.setChecked(dv)
                # conectar: convertir state a bool
                widget.stateChanged.connect(lambda state, k=key, t=tab: self._update_plot_param(t, k, bool(state)))

            # SELECT → QComboBox (espera campo "options" en meta: lista)
            elif param_type == "select":
                widget = QtWidgets.QComboBox()
                options = []
                if isinstance(meta, dict):
                    options = meta.get("options", [])
                # si default_value está en options mostrarlo, si no añadirlo
                for opt in options:
                    widget.addItem(str(opt))
                # set default if present
                if default_value not in (None, "") and str(default_value) not in [str(o) for o in options]:
                    # añadir por si acaso
                    widget.addItem(str(default_value))
                if default_value is not None and default_value != "":
                    index = widget.findText(str(default_value))
                    if index >= 0:
                        widget.setCurrentIndex(index)
                # conectar: enviar texto seleccionado; si necesitas otro tipo, JSON puede indicarlo
                widget.currentTextChanged.connect(lambda value, k=key, t=tab: self._update_plot_param(t, k, value))

            # Opción por defecto (por ejemplo números, listas, dicts) → QLineEdit
            else:
                widget = QtWidgets.QLineEdit()
                if isinstance(default_value, (list, tuple, dict)):
                    widget.setText(json.dumps(default_value))
                else:
                    widget.setText(str(default_value))
                widget.textChanged.connect(lambda value, k=key, t=tab: self._update_plot_param(t, k, value))

            # --- 3️⃣ Añadir al layout ---
            if widget is not None:
                form.addRow(QtWidgets.QLabel(label_text), widget)

            container_widget.updateGeometry()
            container_widget.repaint()

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