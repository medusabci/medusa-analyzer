import os
import json
from PySide6 import QtWidgets, QtCore
from pathlib import Path


class PreprocessingController(QtCore.QObject):
    def __init__(self, ui):
        super().__init__()
        self.view = ui
        self.view.controller = self
        self.experiment_path = None
        self.preprocessing_path = None
        self.path_correct = False
        self.loaded_widgets = False

        # Buttons connects
        self.view.browseButton.clicked.connect(self.browse_folder)

    def browse_folder(self):
        """
        Select a path for the MEDUSA Analyzer experiment.
        """
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            None,
            "Select Experiment Folder",
            QtCore.QDir.currentPath()
        )
        if folder and self.validate_path(folder):
            self.experiment_path = folder
            self.trigger_validation()
            self.view.pathLabel.setText('Selected path: ' + folder)

    def validate_path(self, path):
        """
        Validate the experiment directory and update the view with the results.
        """

        # If path does not exist
        if not os.path.exists(path):
            result = {
                "message": "⚠️ Path does not exist.",
                "experiment_info": None
            }
        # if there is no settings.json file in the path
        else:
            settings_file = os.path.join(path, "settings.json")
            if not os.path.isfile(settings_file):
                result = {
                    "message": "⚠️ settings.json not found in this directory.",
                    "experiment_info": None
                }
            else:
                # Try to read the settings.json file, and extract experiment_type and selected_biosignal
                try:
                    with open(settings_file, "r") as f:
                        data = json.load(f)
                    signal_type = data.get("files", {}).get("selected_biosignal", "Unknown").upper()

                    preprocessed_path = os.path.join(path, "derivatives", "preprocessed")

                    if not os.path.isdir(preprocessed_path):
                        result = {
                            "message": "⚠️ Folder 'derivatives/preprocessed' not found inside experiment directory.",
                        }

                    else:

                        result = {
                            "data_info": {"✅signal_type": signal_type}
                        }
                        self.path_correct = True

                        self.view.main_module.controller.all_files = [str(f) for f in Path(path).rglob('*')
                            if f.is_file() and f.suffix == '.mat']


                # Otherwise, show an error message
                except Exception as e:
                    result = {
                        "message": f"⚠️ Error reading settings.json: {e}",
                        "experiment_info": None
                    }

        # Update the view and save the experiment information.
        if "✅" in result["message"]:
            color = "green"
        else:
            color = "red"
        self.view.messageLabel.setText(f'<span style="color:{color}; font-size:18px;">{result["message"]}</span>')
        return self.path_correct

    def trigger_validation(self):
        """
        Enables or disables the 'Next' button depending on the current state of the controller.
        """

        # The path must be correct
        path_ok = self.path_correct

        # If all conditions are met, enable the 'Next' button
        enable_next = path_ok
        self.view.main_module.nextButton.setEnabled(enable_next)