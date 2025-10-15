from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType

# Load UI class
ui_experiments = loadUiType('data_loader/experiments/view.ui')[0]

class ExperimentWidget(QtWidgets.QWidget, ui_experiments):
    def __init__(self, main_window):
        super().__init__()
        self.setupUi(self)
        self.main_window = main_window

        ### EXPERIMENTS HEADER ###
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.topContentWidget.setLayout(layout)

        self.description_label = QtWidgets.QLabel()
        self.description_label.setTextFormat(QtCore.Qt.RichText)
        self.description_label.setWordWrap(True)
        self.description_label.setAlignment(QtCore.Qt.AlignCenter)
        self.description_label.setOpenExternalLinks(True)

        self.description_label.setText("""
            <div style="text-align:center; font-family:'Segoe UI', Arial;">
                <p style="font-size: 12pt; color:#555; margin:0 40px 10px 40px;">
                    Welcome to <i>MEDUSA Analyzer</i>, a powerful interface for processing biomedical signals.
                </p>

                <p style="font-size: 11pt; color:#777; margin:0 40px;">
                    For more information, see the 
                    <a href="https://docs.medusabci.com/platform/v2024/getstarted.php" 
                       style="color:#007acc; font-weight:bold; text-decoration:none;">
                       manual of use
                    </a>.
                </p>

                <p style="font-size: 12pt; font-weight:600; color:#333; margin-top:15px;">
                    Please select one pipeline to begin.
                </p>
            </div>
        """)

        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Base, palette.color(QtGui.QPalette.Window))
        self.topContentWidget.setPalette(palette)
        self.topContentWidget.setFrameShape(QtWidgets.QFrame.NoFrame)

        layout.addWidget(self.description_label)


        ### ELEMENT CONFIGURATION ###
        # Create radioButton group
        self.button_group = QtWidgets.QButtonGroup(self)
        self.button_group.addButton(self.featureseegRButton)
        self.button_group.addButton(self.featuresecgRButton)
        self.button_group.setExclusive(True)
        # self.featureseegRButton.setChecked(True)

        # Experiment and plot button configuration
        self.featureseegRButton.setProperty("experiment_id", "eeg_features")
        self.featuresecgRButton.setProperty("experiment_id", "ecg_features")

        # Next button configuration
        self.main_window.nextButton.setDisabled(False)
