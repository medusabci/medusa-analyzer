from PySide6 import QtWidgets
from data_loader.converter import conversor_to_rec
from medusa import components
from data_loader.files_list_dialog import FilesListDialog
import os


class DataLoaderController:
    def __init__(self, ui, main_window):
        self.view = ui
        self.main_window = main_window
        self.selected_files = []

        self.view.browseButton.clicked.connect(self.select_files)
        self.view.viewfilesButton.clicked.connect(self.open_file_list_dialog)
        self.view.convertButton.clicked.connect(self.select_and_convert_files)
        self.view.biosignalBox.currentIndexChanged.connect(self.on_combobox_changed)

    def select_files(self):
        """
            Function to select multiple .rec.bson files from various folders.
                - It stores them in 'self.selected_files'.
                - Updates the label with the number of files.
                - If invalid files are selected, prompts to open the converter.
        """
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self.view, "Select recordings", "", "Recording files (*.bson *.json)"
        )

        if not files:
            return

        # Separate .rec.bson and others
        rec_files = [f for f in files if f.endswith(".rec.bson")]
        to_convert = [f for f in files if not f.endswith(".rec.bson")]

        converted_paths = []
        if to_convert:
            QtWidgets.QMessageBox.information(
                self.view,
                "Automatic Conversion",
                f"{len(to_convert)} file(s) are not '.rec.bson' and will be automatically converted."
            )

            self.view.convertLogTextBrowser.clear()
            self.view.convertLogTextBrowser.setVisible(True)
            self.view.convertProgressBar.setValue(0)
            self.view.convertProgressBar.setVisible(True)
            QtWidgets.QApplication.processEvents()

            try:
                # Call converter and get paths of new .rec.bson files
                converted_paths = conversor_to_rec(
                    to_convert,
                    self.view.convertProgressBar,
                    self.view.convertLogTextBrowser,
                    return_rec_paths=True
                )

                QtWidgets.QMessageBox.information(
                    self.view,
                    "Conversion Complete",
                    f"Successfully converted {len(to_convert)} file(s)."
                )
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self.view, "Conversion Error", f"An error occurred during conversion:\n{str(e)}"
                )
                return

            finally:
                self.view.convertProgressBar.setVisible(False)
                self.view.convertLogTextBrowser.setVisible(False)

        # Combine all valid .rec.bson files
        all_rec_files = rec_files + converted_paths

        # Avoid duplicates
        new_files = [f for f in all_rec_files if f not in self.selected_files]
        if not new_files:
            QtWidgets.QMessageBox.information(
                self.view, "No New Files", "All selected files are already loaded."
            )
            return

        self.selected_files.extend(new_files)
        self.update_select_label()

    def update_select_label(self):
        """
            Function to update the text with the number of selected files.
            IMPORTANT: Enables or disables the checkbox and the "Next" button depending on whether files are selected or not.
        """
        count = len(self.selected_files)

        # Update text
        self.view.selectLabel.setText(f"{count} selected files")

        # Sync with main_window
        self.main_window.selected_files = self.selected_files.copy()
        # self.main_window.segmentation_widget.reset_segmentation_state() # TODO check if needed

        if count > 0:
            self.main_window.view.nextButton.setDisabled(False)
            recording = components.Recording.load(self.selected_files[0])
            self.biosignals = recording.biosignals
            for key, value in recording.biosignals.items():
                if value['class_name'] not in ['EEG', 'EMG', 'ECG']:
                    continue
                self.biosignals[key]['fs'] = getattr(recording, key).fs
                try:
                    self.biosignals[key]['num_chann'] = len(getattr(recording, key).channel_set.l_cha)
                except:
                    self.biosignals[key]['num_chann'] = getattr(recording, key).channel_set['n_cha']
                self.view.biosignalBox.addItem(f"Name: {key} - Type: {value['class_name']}")
            self.view.biosignalBox.setCurrentIndex(0)
            default_biosignal = next(iter(recording.biosignals))
            self.main_window.sampling_frequency = getattr(recording, default_biosignal).fs
            self.main_window.num_chann = len(getattr(recording, default_biosignal).channel_set.l_cha)

            # Add elements to biosignalBox

        else:
            self.main_window.view.nextButton.setDisabled(True)
            self.view.biosignalBox.clear()

    def open_file_list_dialog(self):
        """
            Function that opens the file list dialog, and stores the updated file list
        """
        dialog = FilesListDialog(self.selected_files, self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            self.selected_files = dialog.get_updated_files()
            self.update_select_label()

    def select_and_convert_files(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self.view,
            "Select .rcp.bson files to convert",
            "",
            "BSON files (*.*)"
        )

        if not files:
            return

        valid_files = []
        for file in files:
            if not file.endswith(".rcp.bson") and not file.endswith(".mat"):
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
            self.update_select_label()

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self.view,
                "Conversion Error",
                f"An error occurred:\n{str(e)}"
            )
        finally:
            self.view.convertProgressBar.setVisible(False)
            self.view.convertLogTextBrowser.setVisible(False)

    def on_combobox_changed(self):
        """
            Function that updates the sampling frequency and number of channels when the biosignal type is changed.
        """
        selected_biosignal = self.view.biosignalBox.currentText()
        if not selected_biosignal:
            return
        selected_biosignal = selected_biosignal.split(" ")[1]
        self.main_window.sampling_frequency = self.biosignals[selected_biosignal]['fs']
        self.main_window.num_chann = self.biosignals[selected_biosignal]['num_chann']

    def get_data_loader_config(self):
        """
            Function that creates a dictionary with preprocessing configurations.
        """
        config = {
            "selected_files": self.view.selected_files if self.view.selected_files else None,
            "selected_biosignal": self.view.biosignalBox.currentText().split(" ")[1] if self.view.biosignalBox.currentText() else None
        }
        return config