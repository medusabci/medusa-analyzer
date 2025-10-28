from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType


# Load UI class
ui_save_widget = loadUiType("eeg_features/save/view.ui")[0]

class SaveWidget(QtWidgets.QWidget, ui_save_widget):
    """
    Main widget element. Manages the saving options. It also manages the functions to preprocess, segment and
    compute paramters with the previously selected options.
    """
    def __init__(self, main_window):
        super().__init__()
        self.setupUi(self)
        self.main_window = main_window


        ### SAVE HEADER ###
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.topContentWidget.setLayout(layout)
        self.save_label = QtWidgets.QLabel()
        self.save_label.setTextFormat(QtCore.Qt.RichText)
        self.save_label.setWordWrap(True)
        self.save_label.setText("""
            <div style="text-align:center; font-family:'Segoe UI', Arial;">
                <p style="font-size: 12pt; color:#444; margin:0 40px 10px 40px;">
                    Select an <b style="color:#007acc;">empty folder</b> 
                    where the processed data will be saved.
                </p>

                <p style="font-size: 11pt; color:#666; margin:0 40px;">
                    You can choose which types of data from previous 
                    stages of the workflow to export. 
                    All selected data will be saved in the 
                    <b style="color:#ec407a;">.mat format</b>, 
                    ready for further analysis or review.
                </p>
            </div>
        """)
        # Remove background
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Base, palette.color(QtGui.QPalette.Window)) # For this element, Base color will be Window color
        self.topContentWidget.setPalette(palette)
        self.topContentWidget.setFrameShape(QtWidgets.QFrame.NoFrame)
        layout.addWidget(self.save_label)

        ### ELEMENT CONFIGURATION ###

        # Set initial state
        self.progressLabel.hide()
        self.progressBar.hide()
        self.selected_folder = None
        for w in [self.settingsCBox, self.prepsignalsCBox, self.segsignalsCBox, self.paramsignalsCBox]:
            w.setChecked(True)

        # Preparar el spinner (una sola vez, al inicializar la GUI)
        # from PySide6.QtWidgets import QLabel
        # from PySide6.QtGui import QMovie
        # from PySide6.QtCore import Qt
        #
        # self.loadingLabel = QLabel(self)
        # self.loadingLabel.setAlignment(Qt.AlignCenter)  # Centrado
        # self.loadingLabel.setFixedSize(100, 100)  # Tamaño del spinner
        # self.loadingLabel.hide()  # Oculto al inicio
        #
        # self.spinner = QtGui.QMovie("media/spinner.gif")
        # self.loadingLabel.setMovie(self.spinner)
        # self.loadingLabel.hide()
