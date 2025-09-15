import os
import json
from PySide6 import QtWidgets
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication
from eeg_features.core_process import run_pipeline


class SaveController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self

        # Variables
        self.selected_files = []
        self.settings = {}
        self.pipeline_completed = False

        self.view.selectfolderButton.clicked.connect(self.on_selectFolder_clicked)
        self.view.runButton.clicked.connect(self.on_run_clicked)


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
                self.selected_folder = folder
                self.view.selectfolderLabel.setText(folder)
                break



    def save_settings_to_json(self, settings_dic):
        """
        Prepares and saves the configuration parameters into a JSON file.
        """

        # Path to save the JSON file
        self.json_path = os.path.join(self.selected_folder, "settings.json")

        # Save the settings in a JSON file with error handling
        try:
            self._log_message(f"Saving JSON in: {self.json_path}")
            os.makedirs(self.selected_folder, exist_ok=True)  # Create the folder if it does not exist
            with open(self.json_path, "w") as f:
                json.dump(self.settings_dic, f, indent=4)
        except Exception as e:
            self._log_message(f"ERROR SAVING JSON: {e}")
            QtWidgets.QMessageBox.critical(self.view, "Error", f"Could not save the JSON file: {str(e)}")


    def _log_message(self, msg, style=None):
        """
        Logs messages with custom formatting and styles. Used for errors, warnings, and progress info.
        """
        # Styles adapted to the white format
        theme_colors = {
            'THEME_RED': '#D32F2F',  # Darker red
            'THEME_YELLOW': '#FBC02D'  # Darker yellow
        }
        # Format the message based on the style (type of message)
        if isinstance(style, str):
            if style == 'error':
                style = {'color': theme_colors['THEME_RED']}
            elif style == 'warning':
                style = {'color': theme_colors['THEME_YELLOW']}
            # If the style is not recognized, use default
            else:
                style = dict()
        elif style is None:
            style = dict()

        # Set font size
        style.setdefault('font-size', '9pt')
        # Convert style dict to string
        style_str = ';'.join(f'{k}: {v}' for k, v in style.items())
        # Apply the style to the message
        formatted = f'<p style="margin:0;margin-top:2;{style_str}"> >> {msg} </p>'
        # Append the formatted message to the log text browser
        self.view.logtextBrowser.append(formatted)
        self.view.logtextBrowser.moveCursor(QTextCursor.End)
        QApplication.processEvents()
