from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType


# Load UI class
ui_save_widget = loadUiType("eeg_features/save/ui.ui")[0]

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
            <div style="font-size: 11pt; font-family: Arial; line-height: 1;">
                <p>
                    Please select an <b>empty folder</b> where processed data will be saved. This step allows you to export 
                    results from each stage of the workflow.
            </div>
        """)
        # Remove background
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Base, palette.color(QtGui.QPalette.Window)) # For this element, Base color will be Window color
        self.topContentWidget.setPalette(palette)
        layout.addWidget(self.save_label)

        ### ELEMENT CONFIGURATION ###

        # Set initial state
        self.progressLabel.hide()
        self.progressBar.hide()
        self.selected_folder = None
        for w in [self.settingsCBox, self.prepsignalsCBox, self.segsignalsCBox, self.paramsignalsCBox]:
            w.setChecked(True)


        # --- ELEMENT SETUP ---

