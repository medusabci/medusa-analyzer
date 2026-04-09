from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
import medusa.ecg

# Load UI class
ui_plot_widget = loadUiType('plots_stats/timeplot/plot/main_tab_widget.ui')[0]
ui_template = loadUiType('plots_stats/features/plot_panel/tab_template.ui')[0]

class PlotWidget(QtWidgets.QWidget, ui_plot_widget):
    shown = QtCore.Signal()
    def __init__(self, main_module):
        super().__init__()
        self.setupUi(self)
        self.main_module = main_module

        self.tab_widget = self.findChild(QtWidgets.QTabWidget, "tabWidget")
        if self.tab_widget is None:
            raise RuntimeError("No QTabWidget named 'tabWidget' found")

        self.tab_widgets = []  # store references to tab widgets

    def add_tab(self, widget, name: str):
        """Add one tab and save in the list."""
        self.tab_widget.addTab(widget, name)
        self.tab_widgets.append(widget)

    def showEvent(self, event):
        super().showEvent(event)
        self.shown.emit()