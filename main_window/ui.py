import sys
from PySide6 import QtWidgets, QtGui
from PySide6.QtWidgets import QApplication
from PySide6.QtUiTools import loadUiType
from data_loader.ui import DataLoaderWidget
from PySide6.QtGui import QPalette

# Load UI class
ui_main_window = loadUiType('ui.ui')[0]

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

        text = "MEDUSA© Analyzer"
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
        Preprocessing, Segmentation, Signal Analysis, and Downloads.
    """

    def __init__(self):
        super().__init__()

        # Setup UI
        self.setupUi(self)
        # Set the icon
        self.setWindowIcon(QtGui.QIcon("../media/medusa_icon.png"))


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

        # Navigation Buttons
        self.nextButton.setDisabled(True)  # 'Next' is disabled until valid input is provided
        self.nextButton.clicked.connect(self.go_next)
        self.backButton.clicked.connect(self.go_back)
        #
        self.stackedWidget.currentChanged.connect(self.on_tab_changed)


        ### INSERT WORKFLOW WIDGETS INTO STACKEDWIDGET ###

        # Base widget (Data loader)
        self.data_loader = DataLoaderWidget(self)
        self.stackedWidget.insertWidget(0, self.data_loader)
        self.stackedWidget.setCurrentIndex(0)  # Start with the Data Loader tab


    def go_next(self):
        """
            Controls the next (and finish) button behaviour
        """
        idx = self.stackedWidget.currentIndex()
        self.nextButton.setText("Finish" if idx == self.total_steps - 1 else "Next")


    def go_back(self):
        """
            Controls the back button behaviour
        """
        idx = self.stackedWidget.currentIndex()
        self.view.backButton.setVisible(idx > 0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
