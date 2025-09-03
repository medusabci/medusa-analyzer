from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType

# Load UI class
ui_experiments = loadUiType('data_loader/experiments/ui.ui')[0]

class ExperimentWidget(QtWidgets.QWidget, ui_experiments):
    def __init__(self, main_window):
        super().__init__()
        self.setupUi(self)
        self.main_window = main_window


        ### EXPERIMENTS HEADER ###
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self.topContentWidget.setLayout(layout)

        self.description_label = QtWidgets.QLabel()
        self.description_label.setTextFormat(QtCore.Qt.RichText)
        self.description_label.setWordWrap(True)
        self.description_label.setText("""
            <p style="font-size: 11pt; font-family: Arial;">
            Welcome to <i>MEDUSA Analyzer</i>, a graphical interface for processing biomedical signals. 
            For more information, see the <a href="https://editorialcirculorojo.com/feliz-dia-lleno-de-colores/" style="color:#007acc; font-weight:bold; text-decoration:none;">manual of use</a>. <p>
            <p style="font-size: 11pt; font-family: Arial;">
            Please select one experiment to begin.
            </p>
        """)
        # Remove background
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Base, palette.color(QtGui.QPalette.Window))
        self.topContentWidget.setPalette(palette)
        layout.addWidget(self.description_label)


        ### ELEMENT CONFIGURATION ###
        # Create radioButton group
        self.button_group = QtWidgets.QButtonGroup(self)
        self.button_group.addButton(self.featureseegRButton)
        self.button_group.addButton(self.featuresecgRButton)
        self.button_group.setExclusive(True)
        self.featureseegRButton.setChecked(True)

        # Experiment button configuration
        self.featureseegRButton.setProperty("experiment_id", "eeg_features")
        self.featuresecgRButton.setProperty("experiment_id", "ecg_features")

        # Next button configuration
        self.main_window.nextButton.setDisabled(False)