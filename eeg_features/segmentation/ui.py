from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType

# Load UI class
ui_segmentation_widget = loadUiType('eeg_features/segmentation/ui.ui')[0]

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
        layout.setSpacing(2)
        self.topContentWidget.setLayout(layout)
        self.segmentation_label = QtWidgets.QLabel()
        self.segmentation_label.setTextFormat(QtCore.Qt.RichText)
        self.segmentation_label.setWordWrap(True)
        self.segmentation_label.setText("""
            <div style="font-size: 11pt; font-family: Arial; line-height: 1;">
                <p>
                    Proceeding to the <b>Segmentation Module</b>, you can define how the signals should be split 
                    into analyzable segments. Choose between the following segmentation strategies:
            </div>
        """)
        # Remove background
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Base, palette.color(QtGui.QPalette.Window)) # For this element, Base color will be Window color
        self.topContentWidget.setPalette(palette)
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