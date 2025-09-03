from PySide6 import QtWidgets
from data_loader.files.converter import conversor_to_rec
from medusa import components
from data_loader.files.file_list import FilesListDialog
from data_loader.files.converter import CONVERTERS
import os


class FilesController:
    def __init__(self, ui, main_window):
        self.view = ui
        self.main_window = main_window
        self.selected_files = []

        self.view.browseButton.clicked.connect(self.on_select_files_click)
        self.view.viewfilesButton.clicked.connect(self.on_view_files_click)
        self.view.convertButton.clicked.connect(self.on_converter_click)
        self.view.biosignalBox.currentIndexChanged.connect(self.on_biosignal_changed)


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


    def on_file_selection_changed(self):
        """
        Function to update the text with the number of selected files.
        IMPORTANT: Enables or disables the checkbox and the "Next" button depending on whether files are selected or not.
        """
        count = len(self.selected_files)

        # Update text
        self.view.selectLabel.setText(f"{count} selected files")

        # Sync with main_window
        self.main_window.selected_files = self.selected_files.copy()

        if count > 0:
            # Enable the next button
            self.main_window.view.nextButton.setDisabled(False)

            # Get information from the biosignals in the first file
            recording = components.Recording.load(self.selected_files[0])
            self.biosignals = recording.biosignals
            # For each biosignal, get its sampling frequency and number of channels
            for key, value in recording.biosignals.items():

                # Only consider the biosignals in the experiment
                if value['class_name'] not in self.main_window.view.experiment['biosignals']:
                    continue

                # Get the fs (if required)
                if 'fs' in self.main_window.view.experiment['biosignal_information']:
                    self.biosignals[key]['fs'] = getattr(recording, key).fs

                # Get the number of channels (if required), considering ChannelSet as object or dict
                if 'n_chan' in self.main_window.view.experiment['biosignal_information']:
                    try:
                        self.biosignals[key]['n_chan'] = len(getattr(recording, key).channel_set.l_cha)
                    except:
                        self.biosignals[key]['n_chan'] = getattr(recording, key).channel_set['n_cha']

                # Add the biosignal to the biosignal combobox
                self.view.biosignalBox.addItem(f"Name: {key} - Type: {value['class_name']}")

            # Set the default biosignal to the first one
            self.view.biosignalBox.setCurrentIndex(0)
            # Get its fs and number of channels and store them in main_window
            default_biosignal = self.view.biosignalBox.currentText()
            default_biosignal = default_biosignal.split(" ")[1]
            self.main_window.sampling_frequency = getattr(recording, default_biosignal).fs
            self.main_window.n_chan = len(getattr(recording, default_biosignal).channel_set.l_cha)

        else: # No files selected, deactivate the next button and clear the biosignal combobox
            self.main_window.view.nextButton.setDisabled(True)
            self.view.biosignalBox.clear()


    def on_view_files_click(self):
        """
        Function that opens the file list dialog, and stores the updated file list
        """
        dialog = FilesListDialog(self.selected_files, self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            self.selected_files = dialog._update_preprocessing_widget()
            self.on_file_selection_changed()


    def on_converter_click(self):
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
            conversor_to_rec(valid_files, self.view.convertProgressBar, self.view.convertLogTextBrowser)
            QtWidgets.QMessageBox.information(
                self.view,
                "Conversion Complete",
                f"Successfully converted {len(valid_files)} file(s)."
            )

            extension = file.split(".")[-1]
            rec_files = [f.replace("." + extension, ".rec.bson") for f in valid_files]
            for f in rec_files:
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


    def on_biosignal_changed(self):
        """
        Function that updates the sampling frequency and number of channels when the biosignal type is changed.
        """
        selected_biosignal = self.view.biosignalBox.currentText()
        if not selected_biosignal:
            return
        selected_biosignal = selected_biosignal.split(" ")[1]
        self.main_window.sampling_frequency = self.biosignals[selected_biosignal]['fs']
        self.main_window.n_chan = self.biosignals[selected_biosignal]['n_chan']


    def get_data_loader_config(self):
        """
        Function that creates a dictionary with preprocessing configurations.
        """
        config = {
            "selected_files": self.view.selected_files if self.view.selected_files else None,
            "selected_biosignal": self.view.biosignalBox.currentText().split(" ")[1] if self.view.biosignalBox.currentText() else None
        }
        return config