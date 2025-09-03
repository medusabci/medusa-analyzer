from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
import os

# Load UI class
ui_files = loadUiType('data_loader/files/ui.ui')[0]

class FilesWidget(QtWidgets.QWidget, ui_files):
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
            Please, select at least one <span style="color:#007acc; font-weight:bold;">rec</span> file. If not, you can
            use de MEDUSA Converter tool. 
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
        self.set_button_stylesheet(self.convertButton)
        self.set_button_stylesheet(self.explorerButton)
        self.convertProgressBar.setValue(0)
        self.convertProgressBar.setVisible(False)
        self.convertLogTextBrowser.setVisible(False)

        self.explorerButton.setVisible(False)

    def set_button_stylesheet(self, element):
        element.setStyleSheet("""
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