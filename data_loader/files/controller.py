
from data_loader.files.converter import conversor_to_rec
from medusa import components, ecg
from data_loader.files.file_list import FilesListDialog
from data_loader.files.tree_view_list import ExperimentTreeDialog
from data_loader.files.converter import CONVERTERS
from plots.filtering.view import FilteringPlotWidget
import os, json, importlib, time

from PySide6 import QtWidgets, QtCore
import os

class FilesController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self
        self.selected_files = []

        self.view.browseButton.clicked.connect(self.on_select_files_click)
        self.view.viewfilesButton.clicked.connect(self.on_view_files_click)
        self.view.convertButton.clicked.connect(self.on_converter_click)
        self.view.filteringPlotButton.clicked.connect(self.on_filtering_plot_click)
        self.view.loadExperimentButton.clicked.connect(self.on_load_experiment_click)

        self.filtering_window = None

        # Load config
        self.view.loadButton.clicked.connect(self.load_config)

    def on_filtering_plot_click(self):
        if self.filtering_window is None:  # si no existe, la creo
            self.filtering_window = FilteringPlotWidget(self.view.main_window)
        self.filtering_window.show()

    def on_select_files_click(self):
        """
        Function to select multiple .rec.bson files from various folders.
            - It stores them in 'self.selected_files'.
            - Updates the label with the number of files.
            - If invalid files are selected, prompts to open the converter.
        """
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self.view, "Select recordings", "", "Recording files (*.rec.bson)"
        )

        if not files:
            return

        # Include them in the salection and update the label accordingly
        self.selected_files.extend(files)
        self.on_file_selection_changed()
        self.view.loadButton.setEnabled(True)
        self.view.loadLabel.setEnabled(True)


    def on_file_selection_changed(self):
        """
        Function to update the text with the number of selected files.
        IMPORTANT: Enables or disables the checkbox and the "Next" button depending on whether files are selected or not.
        """
        count = len(self.selected_files)

        # Update text
        self.view.selectLabel.setText(f"{count} selected files")

        if count > 0:

            # Loading screen
            self.view.main_window.loading.show()
            self.view.main_window.loading.set_progress(0, self.view.main_window)

            # Enable the next button
            self.view.main_window.nextButton.setDisabled(False)

            # Get information from the biosignals in the first file
            recording = components.Recording.load(self.selected_files[0])
            self.biosignals = recording.biosignals

            # Update loading progress
            self.view.main_window.loading.set_progress(50, self.view.main_window)
            time.sleep(0.5)  # Simulate loading time for better UX

            # For each biosignal, get its sampling frequency and number of channels
            for key, value in recording.biosignals.items():

                # Only consider the biosignals in the experiment
                idx = self.view.main_window.stackedWidget.currentIndex()
                experiment_widget = self.view.main_window.stackedWidget.widget(idx - 1).controller
                if value['class_name'] not in experiment_widget.experiment['biosignals']:
                    continue

                # Get the fs (if required)
                if 'fs' in experiment_widget.experiment['biosignal_information']:
                    self.biosignals[key]['fs'] = getattr(recording, key).fs

                # Get the number of channels (if required), considering ChannelSet as object or dict
                if 'n_chan' in experiment_widget.experiment['biosignal_information']:
                    try:
                        self.biosignals[key]['n_chan'] = len(getattr(recording, key).channel_set.l_cha)
                    except:
                        self.biosignals[key]['n_chan'] = getattr(recording, key).channel_set['n_cha']

                # Get the number of channels (if required), considering ChannelSet as object or dict
                if 'chan_name' in experiment_widget.experiment['biosignal_information']:
                    try:
                        self.biosignals[key]['chan_name'] = getattr(recording, key).channel_set.l_cha
                    except:
                        self.biosignals[key]['chan_name'] = getattr(recording, key).channel_set['l_cha']
                # Add the biosignal to the biosignal combobox
                self.view.biosignalBox.addItem(f"Name: {key} - Type: {value['class_name']}")

            if self.view.biosignalBox.count() == 0:
                QtWidgets.QMessageBox.warning(
                    self.view,
                    "No Valid Biosignals",
                    "The selected file does not contain any biosignal valid for the current experiment.\n"
                    "Please, select another file or convert it to a supported format."
                )
                self.selected_files = []
                self.on_file_selection_changed()
                return

            # Set the default biosignal to the first one
            self.view.biosignalBox.setCurrentIndex(0)

            # Update loading progress
            self.view.main_window.loading.set_progress(100, self.view.main_window)
            time.sleep(0.5)  # Simulate loading time for better UX

            # Finish loading
            self.view.main_window.loading.finish()

        else: # No files selected, deactivate the next button and clear the biosignal combobox
            self.view.main_window.nextButton.setDisabled(True)
            self.view.biosignalBox.clear()


    def on_view_files_click(self):
        """
        Function that opens the file list dialog, and stores the updated file list
        """
        dialog = FilesListDialog(self.selected_files, self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            if self.selected_files != dialog._update_preprocessing_widget():
                self.selected_files = dialog._update_preprocessing_widget()
                self.on_file_selection_changed()


    def on_converter_click(self):
        """
        Function that opens a file dialog to select files to convert, and uses the conversor_to_rec
        """
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self.view,
            "Select files to convert",
            "",
            "All files (*.*)"
        )

        if not files:
            return

        valid_files = []
        for file in files:
            if not any(file.endswith(ext) for ext in CONVERTERS.keys()):
                continue
            extension = file.split(".")[-1]
            rec_path = file.replace("." + extension, ".rec.bson")
            if os.path.exists(rec_path):
                result = QtWidgets.QMessageBox.question(
                    self.view,
                    "File already exists",
                    f"The file '{os.path.basename(rec_path)}' already exists.\nDo you want to overwrite it?",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                )
                if result == QtWidgets.QMessageBox.No:
                    continue
            valid_files.append(file)

        if not valid_files:
            QtWidgets.QMessageBox.information(self.view, "No Valid Files", "No valid files selected for conversion.")
            return

        self.view.convertLogTextBrowser.clear()
        self.view.convertLogTextBrowser.setVisible(True)
        self.view.convertProgressBar.setValue(0)
        self.view.convertProgressBar.setVisible(True)
        QtWidgets.QApplication.processEvents()

        try:
            successfully_converted_files = conversor_to_rec(valid_files, self.view.convertProgressBar, self.view.convertLogTextBrowser)
            QtWidgets.QMessageBox.information(
                self.view,
                "Conversion Complete",
                f"Successfully converted {len(successfully_converted_files)} file(s)."
            )
            # Add the successfully converted files to the selected files, avoiding duplicates
            for f in successfully_converted_files:
                if f not in self.selected_files:
                    self.selected_files.append(f)
            self.on_file_selection_changed()

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self.view,
                "Conversion Error",
                f"An error occurred:\n{str(e)}"
            )
        finally:
            self.view.convertProgressBar.setVisible(False)
            self.view.convertLogTextBrowser.setVisible(False)


    def load_config(self):
        file, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.view, "Select config file", "", "Config file (settings.json)"
        )

        if not file:
            return

        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        experiment_id = self.view.main_window.selected_experiment
        if data['experiment_type'] != self.view.main_window.selected_experiment:
            QtWidgets.QMessageBox.warning(self.view, "Error", "The selected file is not a valid configuration file for this experiment.")
            return

        module_name = f"{experiment_id}.utils"
        mod = importlib.import_module(module_name) # import de module

        # Desactivate warnings in preprocessing controller while loading config
        preprocessing_controller = self.view.main_window.stackedWidget.widget(2).controller # widget(2) is the preprocessing widget
        preprocessing_controller.loading_config = True

        try:
            mod.load_config(self.view, data)
        finally:
            preprocessing_controller.loading_config = False # Re-activate warnings

        self.view.loadLabelAux.setText(f"Configuration loaded from {file}")

    def on_load_experiment_click(self):
        ''' Function to load an experiment structured in semi BIDS format from a folder.'''
        # Open folder dialog
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self.view, "Select experiment folder", ""
        )
        if not folder:
            return

        # Search for .rec.bson files in the folder and its subfolders
        rec_files = []
        for root, _, files in os.walk(folder): # walk the directory tree
            for f in files:
                if f.endswith(".rec.bson"):
                    rec_files.append(os.path.join(root, f))

        if not rec_files:
            QtWidgets.QMessageBox.warning(self.view, "No recordings found",
                                          "No .rec.bson files were found in this folder.")
            return

        # Show the dialog to select files from the tree structure
        dialog = ExperimentTreeDialog(rec_files, experiment_id=self.view.main_window.selected_experiment, parent=self.view)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            selected = dialog.get_selected_files()
            self.selected_files = selected
            self.on_file_selection_changed()
