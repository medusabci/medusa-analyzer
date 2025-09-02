from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
import os

# Load UI class
ui_data_loader = loadUiType('data_loader/ui.ui')[0]

class DataLoaderWidget(QtWidgets.QWidget, ui_data_loader):
    def __init__(self, main_window):
        super().__init__()
        self.setupUi(self)
        self.main_window = main_window

        ### DATA LOADER HEADER ###

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self.topContentWidget.setLayout(layout)
        self.description_label = QtWidgets.QLabel()
        self.description_label.setTextFormat(QtCore.Qt.RichText)
        self.description_label.setWordWrap(True)
        self.description_label.setText("""
            <p style="font-size: 11pt; font-family: Arial;">
            Welcome to <i>MEDUSA Analyzer</i>, a graphical interface for processing biomedical signals. 
            For more information, see the <a href="https://editorialcirculorojo.com/feliz-dia-lleno-de-colores/" style="color:#007acc; font-weight:bold; text-decoration:none;">manual of use</a>. <p>
            <p style="font-size: 11pt; font-family: Arial;">
            Please select one experiment to begin. Then select at least one <span style="color:#007acc; font-weight:bold;">rec</span> file
            </p>
        """)
        # Remove background
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Base,
                         palette.color(QtGui.QPalette.Window))  # For this element, Base color will be Window color
        self.topContentWidget.setPalette(palette)
        layout.addWidget(self.description_label)

        ### ELEMENT CONFIGURATION ###

        # Data loading
        self.selected_files = []  # Store the selected files
        self.main_window.selected_files = self.selected_files
        self.convertButton.setStyleSheet("""
                    QPushButton {
                        color: white;
                        border: none;
                        font-size: 13pt;
                        font-weight: bold;
                        border-radius: 10px;
                        padding: 10px;
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 1, y2: 0,
                            stop: 0 #6a0dad, stop: 1 #ec407a
                        );
                    }
                    QPushButton:hover {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 1, y2: 0,
                            stop: 0 #7b1fa2, stop: 1 #f06292
                        );
                    }
                """)
        self.dataloadergroupBox.setDisabled(True)
        self.convertProgressBar.setValue(0)
        self.convertProgressBar.setVisible(False)
        self.convertLogTextBrowser.setVisible(False)
