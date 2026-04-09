from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
from PySide6.QtGui import QPalette
from utils import LoadingDialog
import ctypes

# Load UI class
ui_main_window = loadUiType('experiments/view.ui')[0]

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

        text = "MEDUSA Analyzer"
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


class MainExperiment(QtWidgets.QMainWindow, ui_main_window):
    """
        Main application window. Manages navigation through the main stages of the workflow:
        preprocessing, segmentation, Signal Analysis, and Downloads.
    """

    def __init__(self):
        super().__init__()

        # Setup UI
        self.setupUi(self)
        # Set application name so it can have its own icon
        medusa_id = u'gib.medusa.analyzer'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(medusa_id)
        # Set icon and title
        self.setWindowIcon(QtGui.QIcon("media/medusa_task_icon.png"))
        self.setWindowTitle("MEDUSA© Analyzer")

        self.backButton.setDisabled(True)

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
        # Variables
        self.current_widget = 0

        ### INSERT WORKFLOW WIDGETS INTO STACKEDWIDGET ###

        ### ADD THE LOADING WINDOW (BUT DO NOT SHOW IT)

        # Waits until the main window is shown to create the loading dialog, so it can be centered over the main window properly
        QtCore.QTimer.singleShot(0, self.show_loading)

    def show_loading(self):
        # Create loading dialog
        self.loading = LoadingDialog(self)


