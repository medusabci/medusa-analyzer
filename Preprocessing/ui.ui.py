from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
import os
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MplCanvas(FigureCanvas):
    """
        Canvas class for the filter canvas
    """
    def __init__(self, parent=None, width=4, height=3, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

# Load UI class
ui_preprocessing = loadUiType('preprocessing/ui.ui')[0]
class EEGParamsPreprocessingWidget(QtWidgets.QWidget, ui_preprocessing):
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
            Please select the preprocessing parameters for your signals. If unsure, default values are provided for common use cases.
            If you don't want to apply any preprocessing step, push the next button. 
            </p>
        """)
        # Remove background
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Base,
                         palette.color(QtGui.QPalette.Window))
        self.topContentWidget.setPalette(palette)
        layout.addWidget(self.description_label)

        ### ELEMENT CONFIGURATION ###

        # Define variables
        self.main_window = main_window
        self.validated_bandpass = False
        self.validating_notch = False
        self.selected_bands = []
        self.band_editor = None
        self.initialized = False

        self.notchCanvas = MplCanvas(self.notchPlotWidget)
        notchLayout = QtWidgets.QVBoxLayout(self.notchPlotWidget)
        notchLayout.addWidget(self.notchCanvas)

        self.bandpassCanvas = MplCanvas(self.bandpassPlotWidget)
        bpLayout = QtWidgets.QVBoxLayout(self.bandpassPlotWidget)
        bpLayout.addWidget(self.bandpassCanvas)

        # Set initial state
        for widget in [self.preprocessingButton, self.preprocessingLabel, self.bandCBox, self.bandsegmentationLabel,
                              self.broadbandLabel, self.broadbandauxLabel, self.hzbroadbandLabel, self.minbroadBox,
                              self.maxbroadBox, self.broadbandButton]:
            widget.setDisabled(True)
        for widget in [self.selectedbandsLabel, self.selectedbandsauxLabel, self.bandLabel, self.bandButton]:
            widget.setVisible(False)

        # Default values in a dict
        self.defaults = {
            "minfreqnotch": self.minfreqnotchBox.value(),
            "maxfreqnotch": self.maxfreqnotchBox.value(),
            "ordernotch": self.orderNotchBox.value(),
            "minfreqbp": self.minfreqbpBox.value(),
            "maxfreqbp": self.maxfreqbpBox.value(),
            "orderbp": self.orderbpBox.value(),
        }