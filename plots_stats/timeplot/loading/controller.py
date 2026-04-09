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
        self.view.subjectlistWidget.itemSelectionChanged.connect(self.trigger_validation)
        self.view.filelistWidget.itemSelectionChanged.connect(self.trigger_validation)
        self.view.searchsubjectEdit.textChanged.connect(self.filter_subj_items)
        self.view.searchfileEdit.textChanged.connect(self.filter_file_items)

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
            self.populate_lists(folder)
            self.view.SubjectSelection.setEnabled(True)
            self.view.FileSelection.setEnabled(True)
        else:
            self.view.subjectlistWidget.clear()
            self.view.filelistWidget.clear()
            self.view.SubjectSelection.setEnabled(False)
            self.view.FileSelection.setEnabled(False)
            self.view.main_module.nextButton.setEnabled(False)

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
                    self.signal_type = data.get("files", {}).get("selected_biosignal", "Unknown").upper()
                    self.channel_list = data["files"]["channel_names"]
                    self.fs = data["preprocessing"]["fs"]

                    preprocessed_path = os.path.join(path, "derivatives", "preprocessed")

                    if not os.path.isdir(preprocessed_path):
                        result = {
                            "message": "⚠️ Folder 'derivatives/preprocessed' not found inside experiment directory.",
                        }

                    else:
                        self.preprocessing_path = preprocessed_path
                        result = {"message": f"✅ Detected preprocessed {self.signal_type} signals"}
                        self.path_correct = True

                # Otherwise, show an error message
                except Exception as e:
                    result = {"message": f"⚠️ Error reading settings.json: {e}"}

        # Update the view and save the experiment information.
        if "✅" in result["message"]:
            color = "green"
        else:
            color = "red"
        self.view.messageLabel.setText(f'<span style="color:{color}; font-size:18px;">{result["message"]}</span>')
        return self.path_correct

    def populate_lists(self, path):
        """
        Fill subjectListWidget and fileListWidget after validating path.
        """
        all_files = [str(f) for f in Path(path).rglob('*') if f.is_file() and f.suffix == '.bson']
        self.subjects = self.get_subjects_from_list(all_files)
        self.recordings = self.get_recordings_from_list(all_files)

        self.view.main_module.controller.all_files = all_files
        self.view.main_module.controller.subjects = self.subjects
        self.view.main_module.controller.recordings = self.recordings

        # Fill list
        self.view.subjectlistWidget.clear()
        if self.subjects:
            self.view.subjectlistWidget.addItems(self.subjects)

        self.view.filelistWidget.clear()
        if self.recordings:
            self.view.filelistWidget.addItems(self.recordings)

        # Enable widgets
        if self.subjects:
            self.view.SubjectSelection.setEnabled(True)
        else:
            self.view.SubjectSelection.setEnabled(False)

        if self.recordings:
            self.view.FileSelection.setEnabled(True)
        else:
            self.view.FileSelection.setEnabled(False)

        self.trigger_validation()

    def get_subjects_from_list(self, recordings):
        """
        Extracts subject identifiers from a list of recording filenames.
        """
        sub_ids = [p for p in (Path(p).parts for p in recordings) for p in p if
                   p.startswith("sub-") and not p.endswith(".bson")]

        sub_ids = list(set(sub_ids))
        sub_ids.sort()

        return sub_ids

    def get_recordings_from_list(self, recordings):
        """
        Extracts subject identifiers from a list of recording filenames.
        """
        keys_to_remove = ["sub", "ses"]

        clean_recordings = []
        for f in recordings:
            p = Path(f)
            stem = p.stem  # Name without extension
            parts = stem.split("_")  # Separate by underscores (assuming BIDS-like structure)
            # Remove parts that start with any of the keys to remove followed by a hyphen
            new_parts = [part for part in parts if not any(part.startswith(k + "-") for k in keys_to_remove)]
            clean_name = "_".join(new_parts)  # Add the rest of the parts back together
            clean_recordings.append(clean_name)

        clean_recordings = list(set(clean_recordings))
        clean_recordings.sort()

        return clean_recordings

    def filter_subj_items(self, text):
        """Filter the subjects in the subject list"""

        if not hasattr(self, 'subjects') or self.subjects is None:
            return

        self.view.subjectlistWidget.clear()

        if not text:
            self.view.subjectlistWidget.addItems(self.subjects)
            return

        text_lower = text.lower()
        filtered = [item for item in self.subjects if text_lower in item.lower()]
        self.view.subjectlistWidget.addItems(filtered)

    def filter_file_items(self, text):
        """Filter the recordings in the list."""

        if not hasattr(self, 'recordings') or self.recordings is None:
            return

        self.view.filelistWidget.clear()
        if not text:
            self.view.filelistWidget.addItems(self.recordings)
            return

        text = text.lower()
        filtered = [item for item in self.recordings if text in item.lower()]
        self.view.filelistWidget.addItems(filtered)

    def trigger_validation(self):
        """
        Enables or disables the 'Next' button depending on the current state of the controller.
        """

        # The path must be correct
        path_ok = self.path_correct
        subject_selected_items = self.view.subjectlistWidget.selectedItems()
        file_selected_items = self.view.filelistWidget.selectedItems()

        if path_ok and len(subject_selected_items) > 0 and len(file_selected_items) > 0:
            subject = subject_selected_items[0].text()
            file_name = file_selected_items[0].text()

            full_file_name = f"{subject}_{file_name}.bson"

            file_path = os.path.join(self.preprocessing_path, subject, self.signal_type, full_file_name)
            self.view.main_module.controller.file_path_to_plot = file_path
            self.view.main_module.controller.channel_list = self.channel_list
            self.view.main_module.controller.fs = self.fs
            self.view.main_module.controller.plot_option = "preprocess"
            self.view.main_module.controller.signal_type = [self.signal_type]

        # If all conditions are met, enable the 'Next' button
        enable_next = path_ok and len(subject_selected_items) > 0 and len(file_selected_items) > 0
        self.view.main_module.nextButton.setEnabled(enable_next)
