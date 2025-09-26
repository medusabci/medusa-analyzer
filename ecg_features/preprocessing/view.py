from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
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
ui_preprocessing = loadUiType('ecg_features/preprocessing/view.ui')[0]

class PreprocessingWidget(QtWidgets.QWidget, ui_preprocessing):
    shown = QtCore.Signal()

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
                    Configure the <b style="color:#ec407a;">preprocessing parameters</b> 
                    for your ECG signals. 
                    You can also enable <b style="color:#8e24aa;">HRV preprocessing</b> 
                    if you plan to analyze heart rate variability.
                </p>

                <p style="font-size: 11pt; color:#666; margin:0 40px;">
                    Default values are provided for typical use cases to help you get started quickly. 
                    If you prefer to <b style="color:#ec407a;">skip preprocessing</b>, 
                    simply click the <b>Next</b> button.
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

        # Define variables
        self.main_window = main_window

        # Initial state preprocessin
        self.cleanCBox.setChecked(False)
        self.zscoreCBox.setChecked(False)
        self.hrvCBox.setChecked(False)
        self.resampleCBox.setChecked(False)

        # Initial state
        for widget in [self.cleanLabel, self.cleanBox, self.cleanButton,
            self.hrvprocessLabel, self.hrvprocessBox, self.hrvprocessButton,
            self.resampleCBox, self.resampleLabel, self.resampleLabelAux, self.resampleLabelNyquist, self.resampleBox]:
            widget.setVisible(False)

        # Default values in a dict
        self.defaults = {
            "resamplefs": self.resampleBox.value()
        }

    def showEvent(self, event):
        super().showEvent(event)
        self.shown.emit()