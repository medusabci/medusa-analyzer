from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication

# Load UI class
ui_files = loadUiType('data_loader/files/view.ui')[0]

class FilesWidget(QtWidgets.QWidget, ui_files):
    def __init__(self, main_window):
        super().__init__()
        self.setupUi(self)
        self.main_window = main_window


        ### DATA LOADER HEADER ###
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.topContentWidget.setLayout(layout)

        self.description_label = QtWidgets.QLabel()
        self.description_label.setTextFormat(QtCore.Qt.RichText)
        self.description_label.setWordWrap(True)
        self.description_label.setAlignment(QtCore.Qt.AlignCenter)

        self.description_label.setText("""
            <div style="text-align:center; font-family:'Segoe UI', Arial;">
                <p style="font-size: 12pt; color:#444; margin:0 40px 10px 40px;">
                    This module allows you to <b>import biomedical recordings</b> 
                    that will be processed in the following steps.
                </p>
            </div>
        """)
        # Remove background
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Base, palette.color(QtGui.QPalette.Window))
        self.topContentWidget.setPalette(palette)
        self.topContentWidget.setFrameShape(QtWidgets.QFrame.NoFrame)

        layout.addWidget(self.description_label)

        ### ELEMENT CONFIGURATION ###

        # Data loading
        self.set_button_stylesheet(self.explorerButton)

        self.explorerButton.setVisible(False)
        self.loadButton.setEnabled(False)
        self.loadLabel.setEnabled(False)

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