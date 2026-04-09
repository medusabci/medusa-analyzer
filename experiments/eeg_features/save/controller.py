import os
import json
from PySide6 import QtWidgets

class SaveController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self

        # Variables
        self.selected_files = []
        self.settings = {}
        self.pipeline_completed = False

        self.view.selectfolderButton.clicked.connect(self.on_selectFolder_clicked)


    def on_selectFolder_clicked(self, *args, **kwargs):
        """
        Lets the user choose an empty folder to save results.
        """

        while True:
            folder = QtWidgets.QFileDialog.getExistingDirectory(self.view, "Select Folder")
            # User cancelled
            if not folder:
                return
            # if the folder is not empty, show a warning and ask again
            if os.listdir(folder):
                QtWidgets.QMessageBox.warning(self.view, "Error", "The selected folder is not empty. Please select an empty folder.")
            # Else, save the folder path and update the label
            else:
                self.view.selected_folder = folder
                self.view.selectfolderLabel.setText(folder)
                break

    def save_settings_to_json(self, settings_dic):
        """
        Prepares and saves the configuration parameters into a JSON file.
        """

        # Add experiment type to the settings dictionary
        settings_dic['experiment_type'] = self.view.main_window.selected_experiment

        # Path to save the JSON file
        self.json_path = os.path.join(self.view.selected_folder, "settings.json")

        # Save the settings in a JSON file with error handling
        try:
            self.view._log_message(f"Saving JSON in: {self.json_path}")
            os.makedirs(self.view.selected_folder, exist_ok=True)  # Create the folder if it does not exist
            with open(self.json_path, "w") as f:
                json.dump(settings_dic, f, indent=4)
        except Exception as e:
            self.view._log_message(f"ERROR SAVING JSON: {e}")
            QtWidgets.QMessageBox.critical(self.view, "Error", f"Could not save the JSON file: {str(e)}")


