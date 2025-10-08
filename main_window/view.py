from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
from data_loader.experiments.view import ExperimentWidget
from data_loader.experiments.controller import ExperimentsController
from PySide6.QtGui import QPalette

# Load UI class
ui_main_window = loadUiType('main_window/view.ui')[0]

class LoadingDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, total_steps=5):
        super().__init__(parent)

        # Dialog box with no borders nor buttons, and always on top
        self.setWindowFlags(
            QtCore.Qt.Dialog |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )
        # Blocks interaction with the parent window
        self.setModal(True)
        # Transparent background
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.total_steps = total_steps

        # --- Style ---
        container = QtWidgets.QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(80, 80, 80, 220);
                border-radius: 8px;
            }
            QLabel { 
                color: white; 
                font-size: 14px;
                font-weight: bold;
                background: transparent; 
            }
            QProgressBar {
                border: 1px solid #888;
                border-radius: 5px;
                text-align: center;
                height: 16px;
            }
            QProgressBar::chunk {
                background-color: #b3b3b3;
                border-radius: 5px;
            }
        """)
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        # Text and progress bar
        self.label = QtWidgets.QLabel("Loading...", alignment=QtCore.Qt.AlignCenter)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        # Layout
        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)
        # Final widget
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.addWidget(container)

        # Center in the parent
        self.set_window_position(parent)


    def set_window_position(self, parent):
        if parent:
            # Dialog size
            dialog_width, dialog_height = 300, 120

            # Parent center in global coordinates
            parent_center = parent.mapToGlobal(parent.rect().center())

            # Upper left coordinates of the dialog to center it
            x = parent_center.x() - dialog_width // 2
            y = parent_center.y() - dialog_height // 2

            self.setGeometry(x, y, dialog_width, dialog_height)


    def set_progress(self, step, parent=None):
        self.progress_bar.setValue(step)
        QtWidgets.QApplication.processEvents()  # Refresh the UI

        # Center in the parent
        self.set_window_position(parent)

    def finish(self):
        QtWidgets.QApplication.processEvents()
        self.accept()  # Close the dialog box


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


class MainWindow(QtWidgets.QMainWindow, ui_main_window):
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

        # Navigation Buttons
        self.nextButton.setDisabled(True)  # 'Next' is disabled until valid input is provided
        self.backButton.setVisible(False)
        self.progressLabel.setVisible(False)

        ### INSERT WORKFLOW WIDGETS INTO STACKEDWIDGET ###

        # Base widget (Data loader)
        self.experiments = ExperimentWidget(self)
        ExperimentsController(self.experiments) # This instantiates the controller and links it to the view
        self.stackedWidget.insertWidget(0, self.experiments)

        ### ADD THE LOADING WINDOW (BUT DO NOT SHOW IT)

        # Waits until the main window is shown to create the loading dialog, so it can be centered over the main window properly
        QtCore.QTimer.singleShot(0, self.show_loading)

    def show_loading(self):
        # Create loading dialog
        self.loading = LoadingDialog(self)


