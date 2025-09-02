from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
import os, json

# Load UI class
ui_experiments = loadUiType('experiments/ui.ui')[0]

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
        # Icons
        self._set_icon(self.eegIcon, "brain2.png", size=130)
        self._set_icon(self.ecgIcon, "heart.png", size=130)
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
        self.main_window.nextButton.clicked.connect(self.on_next_clicked)
        self.main_window.nextButton.setDisabled(False)


    def _set_icon(self, label, filename, size):
        """
        Helper para configurar íconos en QLabel.
        """
        icon_path = os.path.join(os.path.dirname(__file__), "..", "media", filename)
        label.setAlignment(QtCore.Qt.AlignCenter)
        pixmap = QtGui.QPixmap(icon_path)
        label.setPixmap(pixmap.scaled(size, size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        label.setFixedSize(100, 100)


    def on_next_clicked(self):
        """
        Handles the event when the "Next" button is clicked. It loads the selected experiment configuration
        """
        # Get selected experiment
        checked_button = self.button_group.checkedButton()
        experiment_id = checked_button.property("experiment_id")
        # Read the corresponding config file
        with open(experiment_id + "/config.json", "r") as f:
            experiment_data = json.load(f)

            # # Include the Data Loading
            # data_loader = {
            #     "step": "Data Loading",
            #     "path": "data_loader/controller",
            #     "widget": "DataLoaderrController"
            # }
            # # Insert at the beginning of the pipeline
            # experiment_data["pipeline"].insert(0, data_loader)

            self.main_window.experiment = experiment_data

        # Update total steps and progress bar in the main window
        self.main_window.total_steps = len(self.main_window.experiment['pipeline'])
        self.main_window.controller.set_progressbar()

