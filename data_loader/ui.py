from PySide6 import QtWidgets, QtGui
from PySide6.QtUiTools import loadUiType
# from data_loader.ui import DataLoaderWidget
from mock_widget.ui import MockWidget
from PySide6.QtGui import QPalette

# Load UI class
ui_data_loader = loadUiType('data_loader/ui.ui')[0]

class MainWindow(QtWidgets.QMainWindow, ui_data_loader):
    """
        Main application window. Manages navigation through the main stages of the workflow:
        Preprocessing, Segmentation, Signal Analysis, and Downloads.
    """

    def __init__(self, main_window):
        super().__init__()

        # Setup UI
        self.setupUi(self)
        self.main_window = main_window

        ### DATA LOADER HEADER ###



        ### ELEMENT CONFIGURATION ###

