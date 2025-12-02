from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType

# Load UI class
ui_parameters_widget = loadUiType('eeg_features/parameters/view.ui')[0]

class ParametersWidget(QtWidgets.QWidget, ui_parameters_widget):
    """
        Main windget element. Manages the  segmentation configuration of the data. Includes selection of signal markers
        (conditions/events), segmentation window settings, normalization, thresholding, and resampling options.
    """

    def __init__(self, main_window):
        super().__init__()
        # Setup UI
        self.setupUi(self)
        # Define variables
        self.main_window = main_window

        # Define the header (description) of the widget
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.topContentWidget.setLayout(layout)
        self.logtextBrowser = QtWidgets.QLabel()
        self.logtextBrowser.setTextFormat(QtCore.Qt.RichText)
        self.logtextBrowser.setWordWrap(True)
        self.logtextBrowser.setStyleSheet("""
            QLabel {
                background-color: transparent;
                background: transparent;
                border: none;
            }
        """)
        self.logtextBrowser.setText("""
            <div style="text-align:center; font-family:'Segoe UI', Arial;">
                <p style="font-size: 12pt; color:#444; margin:0 40px 10px 40px;">
                    Procceding to the <b>Signal Parameters Module</b> of <i>MEDUSA Analyzer</i>. 
                    Here you can configure a wide range of <b>features and metrics</b> to extract from your EEG 
                    recordings, including statistical descriptors, spectral features, nonlinear parameters, 
                    and connectivity metrics.
                </p>

                <p style="font-size: 11pt; color:#666; margin:0 40px;">
                    Use the checkboxes to select the metrics you want to analyze. Some metrics may require specific 
                    band selections or additional parameters, which can be adjusted after enabling them.
                </p>
            </div>
        """)
        # Remove background
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Base, palette.color(QtGui.QPalette.Window)) # For this element, Base color will be Window color
        self.topContentWidget.setPalette(palette)
        self.topContentWidget.setFrameShape(QtWidgets.QFrame.NoFrame)
        layout.addWidget(self.logtextBrowser)

        # --- ELEMENT SETUP ---

        # RP
        for widget in [self.rpselectedbandsLabel, self.rpselectedbandsauxLabel, self.rpLabel, self.rpButton]:
            widget.setVisible(False)

        # STATISTICS AND NONLINEAR - Element setup
        for widget in [self.ctmrLabel, self.ctmrBox, self.sampenmLabel, self.sampenmBox, self.sampenrLabel, self.sampenrBox,
                       self.maxscaleLabel, self.msampenscaleBox, self.msampenmLabel, self.msampenmBox, self.msampenrLabel,
                       self.msampenrBox, self.mlzcscalesLabel, self.mlzcEdit, self.windowpsdLabel,
                       self.psdcomboBox, self.overlappsdBox, self.segmentpsdBox, self.segmentpsdLabel, self.overlappsdLabel]:
            widget.setVisible(False)

        # CONNECTIVITY - Element setup
        for widget in [self.iacortLabel, self.iacortButton, self.aecortLabel, self.aecortButton]:
            widget.setVisible(False)

        # DEFAULT VALUES
        self.defaults = {
            "psdsegment": self.segmentpsdBox.value(),
            "psdoverlap": self.overlappsdBox.value(),
            "ctmradius": self.ctmrBox.value(),
            "sampm": self.sampenmBox.value(),
            "sampradius": self.sampenrBox.value(),
            "multisampmaxscale": self.msampenscaleBox.value(),
            "multisampm": self.msampenmBox.value(),
            "multisampradius": self.msampenrBox.value(),
        }
