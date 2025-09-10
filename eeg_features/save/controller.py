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
        self.selected_files = []

        self.settings = {}

        self.view.selectfolderButton.clicked.connect(self.select_folder)
        self.view.runButton.clicked.connect(self.run_tasks)

    def handle_exception(func):
        """
            Manages the exceptions
        """
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                if hasattr(self, 'log_message'):
                    self.log_message(f"[ERROR] {func.__name__}: {str(e)}", style='error')
                else:
                    print(f"[ERROR] {func.__name__}: {str(e)}")
        return wrapper

    def prepare_data(self, preprocessing, segmentation, parameters):
        """
            Prepares the configuration parameters for the data processing.
        """
        self.settings_dic = {
            "preprocessing": preprocessing,
            "segmentation": segmentation,
            "parameters": parameters
        }

        self.json_path = os.path.join(self.selected_folder, "settings.json")

        try:
            self.log_message(f"Saving JSON in: {self.json_path}")
            os.makedirs(self.selected_folder, exist_ok=True)  # Create the folder if it do not exist
            with open(self.json_path, "w") as f:
                json.dump(self.settings_dic, f, indent=4)
        except Exception as e:
            self.log_message(f"ERROR SAVING JSON: {e}")
            QtWidgets.QMessageBox.critical(self.view, "Error", f"Could not save the JSON file: {str(e)}")

    def select_folder(self, *args, **kwargs):
        """
            Manages the selection of an empty folder to save the results. It includes all the associated error check
        """

        while True:
            folder = QtWidgets.QFileDialog.getExistingDirectory(self.view, "Select Folder")
            if not folder:
                return  # User cancelled
            if os.listdir(folder):
                QtWidgets.QMessageBox.warning(self.view, "Error", "The selected folder is not empty. Please select an empty folder.")
            else:
                self.selected_folder = folder
                self.view.selectfolderLabel.setText(folder)
                break

    @handle_exception
    def run_tasks(self, *args, **kwargs):
        """
            Main function that runs all the tasks: preprocessing, segmentation and paramters computation.
        """
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

        # Get configuration data
        try:
            preprocessing = self.view.main_window.preproc_widget.get_preprocessing_config()
            segmentation = self.view.main_window.segmentation_widget.get_segmentation_config()
            parameters = self.view.main_window.parameters_widget.get_parameters_config()
        except AttributeError as e:
            QtWidgets.QMessageBox.critical(self.view, "Error",
                                           f"Unable to obtain the data from the main window: {e}")
            return
        self.settings_dic = {
            "preprocessing": preprocessing,
            "segmentation": segmentation,
            "parameters": parameters
        }
        # save the settings
        if self.view.settingsCBox.isChecked():
            self.prepare_data(preprocessing, segmentation, parameters)

        # Run the pipeline
        success = run_pipeline(self, self.settings_dic, total_tasks)
        self.view.main_window.validate_save_step(success)

    def log_message(self, msg, style=None):
        """
            Manages the format of the error and warning messages
        """
        # Styles adapted to the white format
        theme_colors = {
            'THEME_RED': '#D32F2F',  # Darker red
            'THEME_YELLOW': '#FBC02D'  # Darker yellow
        }
        if isinstance(style, str):
            if style == 'error':
                style = {'color': theme_colors['THEME_RED']}
            elif style == 'warning':
                style = {'color': theme_colors['THEME_YELLOW']}
            else:
                style = dict()
        elif style is None:
            style = dict()

        style.setdefault('font-size', '9pt')
        style_str = ';'.join(f'{k}: {v}' for k, v in style.items())

        formatted = f'<p style="margin:0;margin-top:2;{style_str}"> >> {msg} </p>'
        self.view.logtextBrowser.append(formatted)
        self.view.logtextBrowser.moveCursor(QTextCursor.End)
        QApplication.processEvents()
