from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType


# Load UI class
ui_save_widget = loadUiType("ecg_features/leads/view.ui")[0]

class LeadsWidget(QtWidgets.QWidget, ui_save_widget):
    """
    Main widget element.
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
                    BEA TIENES QUE HACER ESTO
                </p>

                <p style="font-size: 11pt; color:#666; margin:0 40px;">
                    ESTO TAMBIÉN 
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