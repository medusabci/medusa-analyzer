from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
import medusa.ecg

# Load UI class
ui_plot_widget = loadUiType('plots_stats/preprocessing/plot/view.ui')[0]


class PlotWidget(QtWidgets.QWidget, ui_plot_widget):
    shown = QtCore.Signal()
    def __init__(self, main_module):
        super().__init__()
        self.setupUi(self)
        self.main_module = main_module


    def showEvent(self, event):
        super().showEvent(event)
        self.shown.emit()