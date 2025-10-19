from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import (QFileDialog, QDialog)

from PySide6.QtUiTools import loadUiType
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from plots_stats.plot_panel.export_dialog import ExportDialog
import re


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

        # For each selected param, we inset one tab in de TabWidget
        for param in param_iter:
            tab = self.load_ui(self.template_ui_path, parent=tab_widget)

            # Modify the title with the param name
            title_label = tab.findChild(QtWidgets.QLabel, "titleLabel")
            if title_label:
                title_label.setText(param)

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
                fig = Figure(figsize=(5, 4))
                canvas = FigureCanvas(fig)
                ax = fig.add_subplot(111)

                fig.tight_layout()
                layout.addWidget(canvas)
                canvas.draw()

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
            self.view.add_tab(tab, str(param))
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