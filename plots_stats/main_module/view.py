from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
from plots_stats.features.config.view import ConfigWidget
from plots_stats.features.config.controller import ConfigController
from PySide6.QtGui import QPalette
from utils import LoadingDialog

# Load UI class
ui_plots_stats_window = loadUiType('plots_stats/main_module/view.ui')[0]


class GradientTitleWidget(QtWidgets.QWidget):
    """
        Creates the header of the MEDUSA Analyzer GUI
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(56)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        font = QtGui.QFont("Arial", 36, QtGui.QFont.Weight.Bold)
        painter.setFont(font)

        text = "Plot & Stats Module"
        fm = QtGui.QFontMetrics(font)
        text_width = fm.horizontalAdvance(text)

        x = (self.width() - text_width) // 2
        y = (self.height() + fm.ascent() - fm.descent()) // 2

        gradient = QtGui.QLinearGradient(x, 0, x + text_width, 0)
        gradient.setColorAt(0.0, QtGui.QColor("#6a0dad"))   # Purple
        gradient.setColorAt(1.0, QtGui.QColor("#ec407a"))   # Pink

        brush = QtGui.QBrush(gradient)
        painter.setPen(QtGui.QPen(brush, 0))
        painter.drawText(x, y, text)


class MainModuleWindow(QtWidgets.QWidget, ui_plots_stats_window):
    """
        Main module window. Manages navigation through the main stages of the workflow.
    """

    def __init__(self):
        super().__init__()
        # Setup UI
        self.setupUi(self)
        # Set the icon
        self.setWindowIcon(QtGui.QIcon("media/medusa_task_icon.png"))


        ### MAIN WINDOW HEADER ###

        # Define the header of the GUI
        self.title_widget = GradientTitleWidget(self)
        # Remove background for the header
        palette = QPalette()
        palette.setColor(QPalette.Base, palette.color(QtGui.QPalette.Window)) # For this element, Base color will be Window color
        self.titleWidget.setPalette(palette)
        # Set the layout for the header
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.title_widget)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(0)
        self.titleWidget.setLayout(layout)


        ### ELEMENT CONFIGURATION ###
        self.current_widget = 0

        # Navigation Buttons
        self.nextButton.setDisabled(True)  # 'Next' is disabled until valid input is provided
        self.backButton.setVisible(False)

        # Waits until the main window is shown to create the loading dialog, so it can be centered over the main window properly
        QtCore.QTimer.singleShot(0, self.show_loading)

    def show_loading(self):
        # Create loading dialog
        self.loading = LoadingDialog(self)

