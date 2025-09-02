from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
import os

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
        self._set_icon(self.eeg_icon, "brain2.png", size=130)
        self._set_icon(self.ecg_icon, "heart.png", size=130)
        self._set_icon(self.medusa_icon, "medusa_icon.png", size=300)

        self.button_group = QtWidgets.QButtonGroup(self)
        self.button_group.addButton(self.featureseegRButton)
        self.button_group.addButton(self.featuresecgRButton)
        self.button_group.setExclusive(True)
        self.featureseegRButton.setChecked(True)

        # Connexions
        self.featureseegRButton.toggled.connect(self.on_tab_experiment)
        self.featuresecgRButton.toggled.connect(self.on_tab_experiment)

    def _set_icon(self, label, filename, size):
        """Helper para configurar íconos en QLabel."""
        icon_path = os.path.join(os.path.dirname(__file__), "..", "media", filename)
        label.setAlignment(QtCore.Qt.AlignCenter)
        pixmap = QtGui.QPixmap(icon_path)
        label.setPixmap(pixmap.scaled(size, size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        label.setFixedSize(100, 100)

    def on_tab_experiment(self):
        """Activa el siguiente paso si hay algún experimento seleccionado."""
        any_checked = (
            self.featureseegRButton.isChecked() or self.featuresecgRButton.isChecked()
        )
        self.main_window.view.nextButton.setEnabled(any_checked)

    def get_experiment_config(self):
        """
            Function that creates a dictionary with preprocessing configurations.
        """
        config = {
            "experiment_name": "eeg_features" if self.featureseegRButton else "ecg_features",
        }
        return config


