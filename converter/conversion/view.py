from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication

# Load UI class
ui_experiments = loadUiType('converter/conversion/view.ui')[0]

class ConversionWidget(QtWidgets.QWidget, ui_experiments):
    def __init__(self, main_window):
        super().__init__()
        self.setupUi(self)
        self.main_window = main_window

        self.convertProgressBar.setValue(0)
        self.convertProgressBar.setVisible(False)
        self.convertLogTextBrowser.setVisible(False)

    def _log_message(self, text):
        self.convertLogTextBrowser.append(text)
        self.convertLogTextBrowser.moveCursor(QTextCursor.End)
        QApplication.processEvents()
