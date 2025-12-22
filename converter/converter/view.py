from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType

# Load UI class
ui_experiments = loadUiType('converter/converter/view.ui')[0]

class ConverterWidget(QtWidgets.QWidget, ui_experiments):
    def __init__(self, main_window):
        super().__init__()
        self.setupUi(self)
        self.main_window = main_window

