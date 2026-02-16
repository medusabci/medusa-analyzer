from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
from converter.data_loader.view import DataLoaderWidget
from converter.data_loader.controller import DataLoaderController
from converter.conversion.view import ConversionWidget
from converter.conversion.controller import ConversionController
from PySide6.QtGui import QPalette
from utils import LoadingDialog
import ctypes

# Load UI class
ui_main_window = loadUiType('converter/view.ui')[0]


class MainConverter(QtWidgets.QMainWindow, ui_main_window):
    """
        Main application window. Manages navigation through the main stages of the workflow:
        preprocessing, segmentation, Signal Analysis, and Downloads.
    """

    def __init__(self):
        super().__init__()

        # Setup UI
        self.setupUi(self)
        # Set application name so it can have its own icon
        medusa_id = u'gib.medusa.converter'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(medusa_id)
        # Set icon and title
        self.setWindowIcon(QtGui.QIcon("media/medusa_task_icon.png"))
        self.setWindowTitle("MEDUSA© Analyzer Converter")

        # Base widget (Data loader)
        self.data_loader = DataLoaderWidget(self)
        DataLoaderController(self.data_loader) # This instantiates the controller and links it to the view
        self.stackedWidget.insertWidget(0, self.data_loader)
        # Second widget (Converter)
        self.converter = ConversionWidget(self)
        ConversionController(self.converter) # This instantiates the controller and links it to the view
        self.stackedWidget.insertWidget(1, self.converter)
        # Start with the data loader view
        self.stackedWidget.setCurrentIndex(0)

