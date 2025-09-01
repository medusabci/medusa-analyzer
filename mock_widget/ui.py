from PySide6 import QtWidgets
from PySide6.QtUiTools import loadUiType

# Load UI class
ui_mock_widget = loadUiType('mock_widget/ui.ui')[0]

class MockWidget(QtWidgets.QWidget, ui_mock_widget):
    """
        Main windget element. Manages all the preprocessing options for the data. Includes CAR, notch filtering and
        bandpass filtering.
    """

    def __init__(self, main_window):
        super().__init__()

        # Setup UI
        self.setupUi(self)

        # Define variables
        self.main_window = main_window