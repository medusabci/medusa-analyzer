from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType

# Load UI class
ui_segmentation_widget = loadUiType('eeg_features/segmentation/view.ui')[0]

class SegmentationWidget(QtWidgets.QWidget, ui_segmentation_widget):
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

        ### SEGMENTATION HEADER ###

        # Define the header (description) of the widget
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.topContentWidget.setLayout(layout)

        self.segmentation_label = QtWidgets.QLabel()
        self.segmentation_label.setTextFormat(QtCore.Qt.RichText)
        self.segmentation_label.setWordWrap(True)
        self.segmentation_label.setAlignment(QtCore.Qt.AlignCenter)

        self.segmentation_label.setText("""
            <div style="text-align:center; font-family:'Segoe UI', Arial;">
                <p style="font-size: 12pt; color:#444; margin:0 40px 10px 40px;">
                    This is the <b style="color:#007acc;">Segmentation Module</b>. 
                    Here you can define how your signals will be divided into 
                    smaller segments for processing.
                </p>

                <p style="font-size: 11pt; color:#666; margin:0 40px;">
                    Select the <b style="color:#00796b;">segmentation strategy</b> that best fits your 
                    analysis needs. 
                    Options include <span style="color:#007acc; font-weight:bold;">time-based slicing</span> 
                    and <span style="color:#ec407a; font-weight:bold;">event-triggered segmentation</span>.
                </p>
            </div>
        """)

        # Remove background
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Base, palette.color(QtGui.QPalette.Window))
        self.topContentWidget.setPalette(palette)
        self.topContentWidget.setFrameShape(QtWidgets.QFrame.NoFrame)

        layout.addWidget(self.segmentation_label)


        ### ELEMENT CONFIGURATION ###

        # Allow multiple selection in condition and event boxes
        self.conditionList.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.eventList.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # Radio buttons should be exclusive within their groups (groups are defined based on their parent)
        self.conditionRButton.setAutoExclusive(True)
        self.eventRButton.setAutoExclusive(True)
        self.zscoreRButton.setAutoExclusive(True)
        self.dcRButton.setAutoExclusive(True)

        # Conditions by default
        self.conditionRButton.setChecked(True)
        # Disable event box by default
        self.eventList.setEnabled(False)
        self.eventList.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.conditionList.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        # DC normalization by default
        self.dcRButton.setChecked(True)

        # Hide elements
        for element in [
            self.baselineLabel_1, self.baselineCBox_1,
            self.baselineLabel_2, self.baselineCBox_2,
            self.zscoreRButton, self.dcRButton,
            self.threskLabel, self.threskBox, self.threskLabelaux,
            self.thressampLabel, self.thressampBox,
            self.threschanLabel, self.threschanBox, self.threshelpButton,
            self.resamplefsBox, self.newfsLabel
        ]:
            element.setVisible(False)

        # Construct the default parameters dictionary
        self.defaults = {
            "triallength": self.trialBox.value(),
            "trialstride": self.trialstrideBox.value(),
            "windowbox1": self.winBox_1.value(),
            "windowbox2": self.winBox_2.value(),
            "baselinewin1": self.baselineCBox_1.value(),
            "baselinewin2": self.baselineCBox_2.value(),
            "threshold": self.threskBox.value(),
            "thressamples": self.thressampBox.value(),
            "threschannels": self.threschanBox.value(),
            "resamplefs": self.resamplefsBox.value(),
        }