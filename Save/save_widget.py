import os
import json
from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QApplication
from core_process import run_pipeline

class SaveWidget(QtWidgets.QWidget):
    """
        Main windget element. Manages the saving options. It also manages the functions to preprocess, segment and
        compute paramters with the previously selected options.
    """
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        uic.loadUi("Save/save_widget.ui", self)

        # Define the header (description) of the widget
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.topContentWidget = self.findChild(QtWidgets.QWidget, "topContentWidget")
        self.topContentWidget.setLayout(layout)
        self.logtextBrowser = QtWidgets.QLabel()
        self.logtextBrowser.setTextFormat(QtCore.Qt.RichText)
        self.logtextBrowser.setWordWrap(True)
        self.logtextBrowser.setText("""
            <div style="font-size: 11pt; font-family: Arial; line-height: 1;">
                <p>
                    Please select an <b>empty folder</b> where processed data will be saved. This step allows you to export 
                    results from each stage of the workflow.
            </div>
        """)
        layout.addWidget(self.logtextBrowser)

        # --- GET ELEMENTS FROM UI MODULE ---
        self.selectfolderButton = self.findChild(QtWidgets.QPushButton, "selectfolderButton")
        self.selectfolderLabel = self.findChild(QtWidgets.QLabel, "selectfolderLabel")
        self.settingsCBox = self.findChild(QtWidgets.QCheckBox, "settingsCBox")
        self.prepsignalsCBox = self.findChild(QtWidgets.QCheckBox, "prepsignalsCBox")
        self.segsignalsCBox = self.findChild(QtWidgets.QCheckBox, "segsignalsCBox")
        self.paramsignalsCBox = self.findChild(QtWidgets.QCheckBox, "paramsignalsCBox")
        self.runButton = self.findChild(QtWidgets.QPushButton, "runButton")
        self.progressLabel = self.findChild(QtWidgets.QLabel, "progressLabel")
        self.progressBar = self.findChild(QtWidgets.QProgressBar, "progressBar")
        self.logtextBrowser = self.findChild(QtWidgets.QTextBrowser, "logtextBrowser")
        self.settings = {}

        # --- ELEMENT SETUP ---
        self.selectfolderButton.clicked.connect(self.select_folder)
        self.runButton.clicked.connect(self.run_tasks)
        # States
        self.progressLabel.hide()
        self.progressBar.hide()
        self.selected_folder = None
        for w in [self.settingsCBox, self.prepsignalsCBox, self.segsignalsCBox, self.paramsignalsCBox]:
            w.setChecked(True)

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
            with open(self.json_path, "w") as f:
                json.dump(self.settings_dic, f, indent=4)
        except Exception as e:
            self.log_message(f"ERROR SAVING JSON: {e}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Could not save the JSON file: {str(e)}")

    def select_folder(self, *args, **kwargs):
        """
            Manages the selection of an empty folder to save the results. It includes all the associated error check
        """

        while True:
            folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Folder")
            if not folder:
                return  # User cancelled

            if os.listdir(folder):
                QtWidgets.QMessageBox.warning(self, "Error",
                                              "The selected folder is not empty. Please select an empty folder.")
            else:
                self.selected_folder = folder
                self.selectfolderLabel.setText(folder)
                break

    @handle_exception
    def run_tasks(self, *args, **kwargs):
        """
            Main function that runs all the tasks: preprocessing, segmentation and paramters computation.
        """
        if not self.selected_folder:
            QtWidgets.QMessageBox.warning(self, "Error", "Please, select one folder to save the data.")
            return

        # Visibility of progress bars
        self.progressLabel.show()
        self.progressBar.show()
        self.progressBar.setValue(0)
        self.error_occurred = False

        # Get the total number of tasks to perform
        total_tasks = sum([
            self.settingsCBox.isChecked(),
            self.prepsignalsCBox.isChecked(),
            self.segsignalsCBox.isChecked(),
            self.paramsignalsCBox.isChecked()
        ])
        total_tasks = max(total_tasks, 1)  # To avoid division by 0

        # Get configuration data
        try:
            preprocessing = self.main_window.preproc_widget.get_preprocessing_config()
            segmentation = self.main_window.segmentation_widget.get_segmentation_config()
            parameters = self.main_window.parameters_widget.get_parameters_config()
        except AttributeError as e:
            QtWidgets.QMessageBox.critical(self, "Error",
                                           f"Unable to obtain the data from the main window: {e}")
            return
        self.settings_dic = {
            "preprocessing": preprocessing,
            "segmentation": segmentation,
            "parameters": parameters
        }
        # Save the settings
        if self.settingsCBox.isChecked():
            self.prepare_data(preprocessing, segmentation, parameters)

        # Run the pipeline
        success = run_pipeline(self, self.settings_dic, total_tasks)
        self.main_window.validate_save_step(success)

    def log_message(self, msg, style=None):
        """
            Manages the format of the error and warning messages
        """
        # Styles adapted to the white format
        theme_colors = {
            'THEME_TEXT_LIGHT': '#333333',  # Dark text (good visibility)
            'THEME_RED': '#D32F2F',  # Darker red
            'THEME_YELLOW': '#FBC02D'  # Darker yellow
        }
        if isinstance(style, str):
            if style == 'error':
                style = {'color': theme_colors['THEME_RED']}
            elif style == 'warning':
                style = {'color': theme_colors['THEME_YELLOW']}
            else:
                style = {'color': theme_colors['THEME_TEXT_LIGHT']}
        elif style is None:
            style = {'color': theme_colors['THEME_TEXT_LIGHT']}

        style.setdefault('font-size', '9pt')
        style_str = ';'.join(f'{k}: {v}' for k, v in style.items())

        formatted = f'<p style="margin:0;margin-top:2;{style_str}"> >> {msg} </p>'
        self.logtextBrowser.append(formatted)
        self.logtextBrowser.moveCursor(QTextCursor.End)
        QApplication.processEvents()

