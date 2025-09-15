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


    def handle_exceptions(func):
        """
        Decorator that manages exceptions raised inside UI actions. Logs the error if possible, otherwise prints it.
        """
        def wrapper(self, *args, **kwargs):
            # Try to run the function
            try:
                return func(self, *args, **kwargs)
            # If Exception
            except Exception as e:
                # Log the error with the custom format, if possible
                if hasattr(self, 'log_message'):
                    self._log_message(f"[ERROR] {func.__name__}: {str(e)}", style='error')
                # Otherwise, print it
                else:
                    print(f"[ERROR] {func.__name__}: {str(e)}")
        return wrapper


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


    @handle_exceptions # Decorator to handle exceptions and log them
    def on_run_clicked(self, *args, **kwargs):
        """
        Executes the pipeline: preprocessing, segmentation, and parameter computation.
        """

        # If no folder is selected, show a warning and return
        if not self.selected_folder:
            QtWidgets.QMessageBox.warning(self.view, "Error", "Please, select one folder to save the data.")
            return

        # Visibility of progress bars
        self.view.progressLabel.show()
        self.view.progressBar.show()
        self.view.progressBar.setValue(0)
        self.view.error_occurred = False

        # Get the total number of tasks to perform
        total_tasks = sum([
            self.view.settingsCBox.isChecked(),
            self.view.prepsignalsCBox.isChecked(),
            self.view.segsignalsCBox.isChecked(),
            self.view.paramsignalsCBox.isChecked()
        ])
        total_tasks = max(total_tasks, 1)  # To avoid division by 0

        # Get configuration data, with error handling
        try:
            files = self.view.main_window.files_widget.get_files_config()
            preprocessing = self.view.main_window.preproc_widget.get_preprocessing_config()
            segmentation = self.view.main_window.segmentation_widget.get_segmentation_config()
            parameters = self.view.main_window.parameters_widget.get_parameters_config()
        except AttributeError as e:
            QtWidgets.QMessageBox.critical(self.view, "Error",
                                           f"Unable to obtain the data from the main window: {e}")
            return

        # Create a settings dictionary grouping all configurations
        self.settings_dic = {
            "files": files,
            "preprocessing": preprocessing,
            "segmentation": segmentation,
            "parameters": parameters
        }
        # Save the settings dict
        if self.view.settingsCBox.isChecked():
            self.save_settings_to_json(self.settings_dic)

        # Run the pipeline
        success = run_pipeline(self, self.settings_dic, total_tasks)

        if success:
            self.view.main_window.nextButton.setText('Close')
