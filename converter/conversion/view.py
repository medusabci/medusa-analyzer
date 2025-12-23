from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType

# Load UI class
ui_experiments = loadUiType('converter/conversion/view.ui')[0]

class ConversionWidget(QtWidgets.QWidget, ui_experiments):
    def __init__(self, main_window):
        super().__init__()
        self.setupUi(self)
        self.main_window = main_window

    def _log_message(self, text):
        self.convertLogTextBrowser.append(text)
        self.convertLogTextBrowser.moveCursor(QTextCursor.End)
        QApplication.processEvents()
