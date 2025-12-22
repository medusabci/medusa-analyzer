from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
from converter.data_loader.view import DataLoaderWidget
from converter.data_loader.controller import DataLoaderController
from converter.converter.view import ConverterWidget
from converter.converter.controller import ConverterController
from PySide6.QtGui import QPalette
from utils import LoadingDialog

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
        # Set the icon
        self.setWindowIcon(QtGui.QIcon("media/medusa_icon.png"))

        # Base widget (Data loader)
        self.data_loader = DataLoaderWidget(self)
        DataLoaderController(self.data_loader) # This instantiates the controller and links it to the view
        self.stackedWidget.insertWidget(0, self.data_loader)
        # Second widget (Converter)
        self.converter = ConverterWidget(self)
        ConverterController(self.converter) # This instantiates the controller and links it to the view
        self.stackedWidget.insertWidget(1, self.converter)
        # Start with the data loader view
        self.stackedWidget.setCurrentIndex(0)

