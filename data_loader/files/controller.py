from pathlib import Path
from data_loader.files.converter import ConverterWorker
from medusa import components, ecg
from data_loader.files.file_list import FilesListDialog
from data_loader.files.tree_view_list import ExperimentTreeDialog, GenericFileTreeDialog
from data_loader.files.converter import CONVERTERS
import os, json, importlib, time
from PySide6.QtCore import Qt


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
        self.view.loadExperimentButton.clicked.connect(self.on_load_experiment_click)

        self.filtering_window = None

        # Load config
        self.view.loadButton.clicked.connect(self.load_config)
        self.view.main_window.nextButton.setDisabled(True)

    def on_select_files_click(self):
        """
        Function to select multiple .rec.bson files from various folders.
            - It stores them in 'self.selected_files'.
            - Updates the label with the number of files.
            - If invalid files are selected, prompts to open the converter.
        """
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self.view, "Select recordings", "", "Recording files (*.rec.bson)")

        if not files:
            return

        # Include them in the selection and update the label accordingly
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
            time.sleep(1)  # Simulate loading time for better UX

            # For each biosignal, get its sampling frequency and number of channels
            for key, value in recording.biosignals.items():

                # Only consider the biosignals in the experiment
                idx = self.view.main_window.stackedWidget.currentIndex()
                experiment_widget = self.view.main_window.stackedWidget.widget(idx - 1).controller
                if value['class_name'] not in experiment_widget.experiment['biosignals']:
                    continue

                # Get de channel list
                channel_set = getattr(recording, key).channel_set
                self.channels = getattr(channel_set, 'l_cha',
                                   channel_set.get('l_cha') if isinstance(channel_set, dict) else None)

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
                # Finish loading
                self.view.main_window.loading.finish()

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
        Opens a dialog that allows the user to select a directory containing data files
        to be converted, displays a tree-view dialog to select specific files, and runs `conversor_to_rec` on the
        chosen files.
        """
        msg = QtWidgets.QMessageBox(self.view)
        msg.setWindowTitle("Data Conversion Wizard")
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setTextFormat(QtCore.Qt.RichText)
        msg.setText(
            "<b>Welcome to the Data Conversion Wizard</b><br><br>"
            "This tool helps you convert supported data files into the <b>.rec.bson</b> format.<br><br>"
            "✅ You can select a <b>root directory</b> (e.g., <i>data/</i>) that contains your files.<br>"
            "✅ All subfolders will be scanned automatically.<br>"
            "✅ You can then choose which files to include in the conversion.<br><br>"
            "Click <b>OK</b> to continue and select the root folder."
        )
        msg.exec()

        # Select the root input directory
        input_dir = str(QtWidgets.QFileDialog.getExistingDirectory(self.view,"Select Root Directory Containing Data to Convert"))
        if not input_dir:
            QtWidgets.QMessageBox.information(self.view, "Operation cancelled", "No folder was selected. Conversion aborted.")
            return

        # Loading screen
        self.view.main_window.loading.show()
        self.view.main_window.loading.set_progress(50, self.view.main_window)

        # Gather valid files recursively
        valid_exts = tuple(CONVERTERS.keys())
        rec_files = [os.path.join(root, f) for root, _, files in os.walk(input_dir) for f in files if f.endswith(valid_exts)]

        # Loading screen
        self.view.main_window.loading.set_progress(100, self.view.main_window)
        time.sleep(0.5) # Simulate loading time for better UX

        if not rec_files:
            QtWidgets.QMessageBox.warning(
                self.view,
                "No Valid Files Found",
                f"No supported files were detected in:\n{input_dir}\n\n"
                f"Supported extensions: {', '.join(valid_exts)}"
            )
            return

        # Prepare the UI for conversion
        self.view.convertLogTextBrowser.clear()
        self.view.convertLogTextBrowser.setVisible(True)
        self.view.convertProgressBar.setValue(0)
        self.view.convertProgressBar.setVisible(True)
        QtWidgets.QApplication.processEvents()

        # Disable the button while the pipeline is running
        self.view.main_window.nextButton.setEnabled(False)

        # Finish loading
        self.view.main_window.loading.finish()

        # Display the file selection tree
        dialog = GenericFileTreeDialog(rec_files, parent=self.view)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            QtWidgets.QMessageBox.information(self.view, "Cancelled", "No files were selected for conversion.")
            return

        selected_files = dialog.get_selected_files()
        if not selected_files:
            QtWidgets.QMessageBox.information(self.view, "No Selection", "No files were selected for conversion.")
            return

        # Create the thread
        output_path = self._select_output_directory()
        experiment_type = getattr(self.view.main_window, "selected_experiment", "").split('_')[0].upper()
        self.view.worker = ConverterWorker(selected_files, experiment_type, output_path, input_dir)

        # Connect the signals to the functions
        self.view.worker.progress.connect(self.view.convertProgressBar.setValue, type=Qt.QueuedConnection)
        self.view.worker.log.connect(self.view._log_message, type=Qt.QueuedConnection)

        # Clean up when done
        self.view.worker.finished.connect(self.view.worker.deleteLater)

        # When the worker is finished, enable the button and change its text
        def on_finished(converted_files, error_found):
            if error_found:
                QtWidgets.QMessageBox.critical(
                    self.view,
                    "Conversion Error",
                    f"❌ An unexpected error occurred during conversion:\n\n"
                )
            else:
                QtWidgets.QMessageBox.information(
                    self.view,
                    "Conversion Complete",
                    f"✅ Successfully converted {len(converted_files)} file(s)."
                )

            # Add the successfully converted files to the selected files, avoiding duplicates
            new_files = [f for f in converted_files if f not in self.selected_files]
            self.selected_files.extend(new_files)
            self.on_file_selection_changed()

            # Always restore the UI state
            self.view.convertProgressBar.setVisible(False)
            self.view.convertLogTextBrowser.setVisible(False)

        # Connect the on_finished function
        self.view.worker.finished.connect(on_finished)

        # Run the thread
        self.view.worker.start()

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

        # Enable config
        self.view.loadButton.setEnabled(True)
        self.view.loadLabel.setEnabled(True)

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

    def _select_output_directory(self):
        """Ask the user for output directory and prepare folders."""
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle("Select output path")
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText(
            f"Starting the conversion.\n\n"
            "First, select a folder to save files in semi-BIDS format.\n\n"
            "Note that original files will not be modified."
        )
        msg.exec()

        output_path = QtWidgets.QFileDialog.getExistingDirectory(
            None,
            "Select destination folder for converted files (semi-BIDS root)"
        )
        if not output_path:
            self.view._log_message("🚫 Conversion cancelled (no output folder selected).")
            return None

        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        self.view._log_message(f"📁 Output path selected: {output_dir}")
        return output_dir