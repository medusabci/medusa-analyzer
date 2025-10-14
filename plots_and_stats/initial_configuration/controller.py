import os
import json
from PySide6 import QtWidgets, QtCore
from . import flow

# plots_and_stats/initial_configuration/controller.py
class PlotStatsInitController(QtCore.QObject):


    def __init__(self, view, parent=None):
        super().__init__(parent)
        self.view = view

        self.view.browseButton.clicked.connect(self.browse_folder)
        self.view.pathEdit.textChanged.connect(self.validate_path)
        self.existingPathCorrect = False
        self.main_window_controller = None

        self.view.withinRButton.toggled.connect(lambda: self.trigger_validation())
        self.view.betweenRButton.toggled.connect(lambda: self.trigger_validation())
        self.view.preprocessedRButton.toggled.connect(lambda: self.trigger_validation())
        self.view.parametersRButton.toggled.connect(lambda: self.trigger_validation())
        self.view.pathEdit.textChanged.connect(lambda: self.trigger_validation())

    def browse_folder(self):
        print("browse_folder called")
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            None,
            "Select Experiment Folder",
            QtCore.QDir.currentPath()
        )
        print("Selected folder:", folder)
        if folder:
            self.view.pathEdit.setText(folder)

    def validate_path(self):
        """Valida el directorio del experimento y actualiza la vista con los resultados."""
        path = self.view.pathEdit.text().strip()

        if not os.path.exists(path):
            result = {
                "message": "⚠️ Path does not exist.",
                "expinfo": "",
                "experiment_info": None
            }
        else:
            settings_file = os.path.join(path, "settings.json")
            if not os.path.isfile(settings_file):
                result = {
                    "message": "⚠️ settings.json not found in this directory.",
                    "expinfo": "",
                    "experiment_info": None
                }
            else:
                try:
                    with open(settings_file, "r") as f:
                        data = json.load(f)
                    exp_type = data.get("experiment_type", "Unknown")
                    signal_type = data.get("files", {}).get("selected_biosignal", "Unknown").upper()
                    result = {
                        "message": "",
                        "expinfo": f"✅ Detected Experiment: {exp_type} ({signal_type})",
                        "experiment_info": {"experiment_type": exp_type, "signal_type": signal_type}
                    }
                    self.existingPathCorrect = True
                except Exception as e:
                    result = {
                        "message": f"⚠️ Error reading settings.json: {e}",
                        "expinfo": "",
                        "experiment_info": None
                    }

        # Actualiza la vista y guarda la información del experimento
        self.view.messageLabel.setText(result["message"])
        self.view.expinfoLabel.setText(result["expinfo"])
        self.experiment_info = result["experiment_info"]

    def trigger_validation(self):
        if self.main_window_controller is not None:
            flow.validate_initial_configuration(self, self.main_window_controller)
