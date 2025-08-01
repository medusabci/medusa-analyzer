import os
import json
from PyQt5 import QtWidgets, uic
from core.pipeline import run_pipeline

class DownloadWidget(QtWidgets.QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        uic.loadUi("save_widget.ui", self)

        self.selectfolderButton = self.findChild(QtWidgets.QPushButton, "selectfolderButton")
        self.selectfolderLabel = self.findChild(QtWidgets.QLabel, "selectfolderLabel")
        self.settingsCBox = self.findChild(QtWidgets.QCheckBox, "settingsCBox")
        self.prepsignalsCBox = self.findChild(QtWidgets.QCheckBox, "prepsignalsCBox")
        self.segsignalsCBox = self.findChild(QtWidgets.QCheckBox, "segsignalsCBox")
        self.paramsignalsCBox = self.findChild(QtWidgets.QCheckBox, "paramsignalsCBox")
        self.runButton = self.findChild(QtWidgets.QPushButton, "runButton")
        self.progressLabel = self.findChild(QtWidgets.QLabel, "progressLabel")
        self.progressBar = self.findChild(QtWidgets.QProgressBar, "progressBar")
        self.settings = {}

        # Estados
        self.progressLabel.hide()
        self.progressBar.hide()
        self.selected_folder = None

        # Connect buttons
        self.selectfolderButton.clicked.connect(self.select_folder)
        self.runButton.clicked.connect(self.run_tasks)

    def prepare_data(self, preprocessing, segmentation, parameters):
        self.settings_dic = {
            "preprocessing": preprocessing,
            "segmentation": segmentation,
            "parameters": parameters
        }

        self.json_path = os.path.join(self.selected_folder, "settings.json")

        try:
            print(f"Guardando JSON en: {self.json_path}")
            with open(self.json_path, "w") as f:
                json.dump(self.settings_dic, f, indent=4)
        except Exception as e:
            print(f"ERROR AL GUARDAR JSON: {e}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Could not save the JSON file: {str(e)}")

    def select_folder(self):
        while True:
            folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Folder")
            if not folder:
                return

            if os.listdir(folder):
                QtWidgets.QMessageBox.warning(self, "Error",
                                              "The selected folder is not empty. Please select an empty folder.")
            else:
                self.selected_folder = folder
                QtWidgets.QMessageBox.information(self, "Selected folder", f"It has been selected: {folder}")
                break

    def run_tasks(self):
        if not self.selected_folder:
            QtWidgets.QMessageBox.warning(self, "Error", "Please, select one folder to save the data.")
            return

        self.progressLabel.show()
        self.progressBar.show()
        self.progressBar.setValue(0)

        total_tasks = sum([
            self.settingsCBox.isChecked(),
            self.prepsignalsCBox.isChecked(),
            self.segsignalsCBox.isChecked(),
            self.paramsignalsCBox.isChecked()
        ])
        total_tasks = max(total_tasks, 1)

        try:
            preprocessing = self.main_window.preproc_widget.get_preprocessing_config()
            segmentation = self.main_window.segmentation_widget.get_segmentation_config()
            parameters = self.main_window.parameters_widget.get_parameters_config()
        except AttributeError as e:
            QtWidgets.QMessageBox.critical(self, "Error",
                                           f"Unable to obtain the data from the main window: {e}")
            return

        if self.settingsCBox.isChecked():
            self.prepare_data(preprocessing, segmentation, parameters)

        self.settings_dic = {
            "preprocessing": preprocessing,
            "segmentation": segmentation,
            "parameters": parameters
        }

        checkboxes = {
            'prep': self.prepsignalsCBox.isChecked(),
            'seg': self.segsignalsCBox.isChecked(),
            'param': self.paramsignalsCBox.isChecked()
        }

        run_pipeline(self.settings_dic, self.selected_folder, checkboxes, self.update_progress)

        QtWidgets.QMessageBox.information(self, "Download Complete", "Files downloaded successfully.")

    def update_progress(self, value, label):
        self.progressLabel.setText(label)
        self.progressBar.setValue(value)
        QtWidgets.QApplication.processEvents()