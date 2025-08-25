from PyQt5 import QtWidgets, uic, QtGui, QtCore
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from Preprocessing.files_list_dialog import FilesListDialog
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy.signal import firwin, freqz
from bands_table import BandTable
import numpy as np
import os
from conversor_to_rec import conversor_to_rec
from medusa import components

class MplCanvas(FigureCanvas):
    """
        Canvas class for the filter canvas
    """
    def __init__(self, parent=None, width=4, height=3, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

class PreprocessingWidget(QtWidgets.QWidget):
    """
        Main windget element. Manages all the preprocessing options for the data. Includes CAR, notch filtering and
        bandpass filtering.
    """

    band_config_changed = QtCore.pyqtSignal()

    def __init__(self, main_window):
        super().__init__()
        uic.loadUi("Preprocessing/preprocessing_widget.ui", self)

        # Define variables
        self.main_window = main_window
        self.validated_bandpass = False
        self.validating_notch = False
        self.selected_bands = []
        self.band_editor = None  # It will be initialized later
        self.initialized = False  # Para que manejar los parámetros por defecto

        # Define the header (description) of the widget
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self.topContentWidget = self.findChild(QtWidgets.QWidget, "topContentWidget")
        self.topContentWidget.setLayout(layout)
        self.description_label = QtWidgets.QLabel()
        self.description_label.setTextFormat(QtCore.Qt.RichText)
        self.description_label.setWordWrap(True)
        self.description_label.setText("""
                <p style="font-size: 11pt; font-family: Arial;">
                Welcome to the <b>Preprocessing Module</b> of <i>MEDUSA Analyzer</i>. 
                Please select at least one <span style="color:#007acc; font-weight:bold;">rec</span> file to begin.
                </p>
                """)
        layout.addWidget(self.description_label)

        # --- GET ELEMENTS FROM UI MODULE ---

        # Data loading
        self.browseButton = self.findChild(QtWidgets.QPushButton, "browseButton")
        self.viewfilesButton = self.findChild(QtWidgets.QPushButton, "viewfilesButton")
        self.selectLabel = self.findChild(QtWidgets.QLabel, "selectLabel")
        self.selected_files = []  # Store the selected files
        self.convertButton = self.findChild(QtWidgets.QPushButton, "convertButton")
        self.convertButton.setStyleSheet("""
            QPushButton {
                color: white;
                border: none;
                font-size: 13pt;
                font-weight: bold;
                border-radius: 10px;
                padding: 10px;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #6a0dad, stop: 1 #ec407a
                );
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #7b1fa2, stop: 1 #f06292
                );
            }
        """)
        self.convertProgressBar = self.findChild(QtWidgets.QProgressBar, "convertProgressBar")
        self.convertProgressBar.setValue(0)
        self.convertProgressBar.setVisible(False)
        self.convertLogTextBrowser = self.findChild(QtWidgets.QTextBrowser, "convertLogTextBrowser")
        self.convertLogTextBrowser.setVisible(False)
        self.broadbandButton = self.findChild(QtWidgets.QToolButton, "broadbandButton")
        self.broadbandLabel = self.findChild(QtWidgets.QLabel, "broadbandLabel")
        self.minbroadBox = self.findChild(QtWidgets.QDoubleSpinBox, "minbroadBox")
        self.broadbandauxLabel = self.findChild(QtWidgets.QLabel, "broadbandauxLabel")
        self.maxbroadBox = self.findChild(QtWidgets.QDoubleSpinBox, "maxbroadBox")
        self.hzbroadbandLabel = self.findChild(QtWidgets.QLabel, "hzbroadbandLabel")
        # Preprocessing
        self.preprocessingButton = self.findChild(QtWidgets.QCheckBox, "preprocessingButton")
        self.preprocessingLabel = self.findChild(QtWidgets.QLabel, "preprocessingLabel")
        # Notch
        self.notchgroupBox = self.findChild(QtWidgets.QGroupBox, "notchgroupBox")
        self.notchLabel = self.findChild(QtWidgets.QLabel, "notchfilterLabel")
        self.notchCBox = self.findChild(QtWidgets.QCheckBox, "notchCBox")
        self.notchminLabel = self.findChild(QtWidgets.QLabel, "notchminLabel")
        self.minfreqnotchBox = self.findChild(QtWidgets.QDoubleSpinBox, "minfreqnotchBox")
        self.notchmaxLabel = self.findChild(QtWidgets.QLabel, "notchmaxLabel")
        self.maxfreqnotchBox = self.findChild(QtWidgets.QDoubleSpinBox, "maxfreqnotchBox")
        self.orderNotchLabel = self.findChild(QtWidgets.QLabel, "orderNotchLabel")
        self.orderNotchBox = self.findChild(QtWidgets.QSpinBox, "orderNotchBox")
        self.winnotchLabel = self.findChild(QtWidgets.QLabel, "winnotchLabel")
        self.winnotchBox = self.findChild(QtWidgets.QComboBox, "winnotchBox")
        self.winbpLabel = self.findChild(QtWidgets.QLabel, "winbpLabel")
        self.winbpBox = self.findChild(QtWidgets.QComboBox, "winbpBox")
        self.notchPlotWidget = self.findChild(QtWidgets.QWidget, "notchPlotWidget")
        self.drawnotchButton = self.findChild(QtWidgets.QPushButton, "drawnotchButton")
        self.notchCanvas = MplCanvas(self.notchPlotWidget)
        notchLayout = QtWidgets.QVBoxLayout(self.notchPlotWidget)
        notchLayout.addWidget(self.notchCanvas)
        # Bandpass
        self.bpgroupBox = self.findChild(QtWidgets.QGroupBox, "bpgroupBox")
        self.bpLabel = self.findChild(QtWidgets.QLabel, "bpLabel")
        self.bpCBox = self.findChild(QtWidgets.QCheckBox, "bpCBox")
        self.bpminLabel = self.findChild(QtWidgets.QLabel, "bpminfreqLabel")
        self.minfreqbpBox = self.findChild(QtWidgets.QDoubleSpinBox, "minfreqbpBox")
        self.bpmaxLabel = self.findChild(QtWidgets.QLabel, "bpmaxfreqLabel")
        self.maxfreqbpBox = self.findChild(QtWidgets.QDoubleSpinBox, "maxfreqbpBox")
        self.orderbpLabel = self.findChild(QtWidgets.QLabel, "orderbpLabel")
        self.orderbpBox = self.findChild(QtWidgets.QSpinBox, "orderbpBox")
        self.bandpassPlotWidget = self.findChild(QtWidgets.QWidget, "bandpassPlotWidget")
        self.drawbpButton = self.findChild(QtWidgets.QPushButton, "drawbpButton")
        self.bandpassCanvas = MplCanvas(self.bandpassPlotWidget)
        bpLayout = QtWidgets.QVBoxLayout(self.bandpassPlotWidget)
        bpLayout.addWidget(self.bandpassCanvas)
        # CAR
        self.cargroupBox = self.findChild(QtWidgets.QGroupBox, "cargroupBox")
        self.carLabel = self.findChild(QtWidgets.QLabel, "carLabel")
        self.carCBox = self.findChild(QtWidgets.QCheckBox, "carCBox")
        # Band segmentation
        self.bandCBox = self.findChild(QtWidgets.QCheckBox, "bandCBox")
        self.selectedbandsLabel = self.findChild(QtWidgets.QLabel, "selectedbandsLabel")
        self.selectedbandsauxLabel = self.findChild(QtWidgets.QLabel, "selectedbandsauxLabel")
        self.bandLabel = self.findChild(QtWidgets.QLabel, "bandLabel")
        self.bandButton = self.findChild(QtWidgets.QPushButton, "bandButton")
        self.bandsegmentationLabel = self.findChild(QtWidgets.QLabel, "bandsegmentationLabel")
        self.element_group = [self.preprocessingButton, self.preprocessingLabel, self.bandCBox, self.bandsegmentationLabel,
                         self.broadbandLabel, self.broadbandauxLabel, self.hzbroadbandLabel, self.minbroadBox,
                         self.maxbroadBox, self.broadbandButton]

        # --- ELEMENT SETUP ---

        # Data loading
        self.browseButton.clicked.connect(self.select_files)
        self.viewfilesButton.clicked.connect(self.open_file_list_dialog)
        self.convertButton.clicked.connect(self.select_and_convert_files)
        self.broadbandButton.clicked.connect(self.show_freq_content_dialog)
        # Data preprocessing
        self.preprocessingButton.toggled.connect(self.toggle_preprocessing_group)
        self.preprocessingButton.toggled.connect(self.update_select_label)
        # Broadband
        self.minbroadBox.valueChanged.connect(self.disable_bandsegmentation_on_bp_change)
        self.maxbroadBox.valueChanged.connect(self.disable_bandsegmentation_on_bp_change)
        # Notch
        self.notchCBox.toggled.connect(self.toggle_notch_controls)
        self.notchCBox.toggled.connect(lambda: self.update_filter_plot('notch'))
        self.drawnotchButton.clicked.connect(lambda: self.update_filter_plot('notch'))
        # Get the BG color and apply it
        bg_color = self.palette().color(self.backgroundRole()).name()
        self.notchCanvas.fig.patch.set_facecolor(bg_color)
        self.notchCanvas.ax.set_facecolor(bg_color)
        # Bandpass
        self.bpCBox.toggled.connect(self.toggle_bandpass_controls)
        self.bpCBox.toggled.connect(lambda: self.update_filter_plot('bandpass'))
        self.drawbpButton.clicked.connect(lambda: self.update_filter_plot('bandpass'))
        self.bandpassCanvas.fig.patch.set_facecolor(bg_color)
        self.bandpassCanvas.ax.set_facecolor(bg_color)
        self.minfreqbpBox.valueChanged.connect(lambda: self.minbroadBox.setValue(self.minfreqbpBox.value()))
        self.maxfreqbpBox.valueChanged.connect(lambda: self.maxbroadBox.setValue(self.maxfreqbpBox.value()))
        self.minfreqbpBox.valueChanged.connect(self.disable_bandsegmentation_on_bp_change)
        self.maxfreqbpBox.valueChanged.connect(self.disable_bandsegmentation_on_bp_change)

        # Band segmentation
        self.bandCBox.toggled.connect(self.toggle_bands_segmentation)
        self.bandButton.clicked.connect(lambda: self.open_band_editor("segmentation"))
        # Sync changes in spinboxed with the band table content
        # self.minbroadBox.editingFinished.connect(self._sync_broadband_spinboxes)
        # self.maxbroadBox.editingFinished.connect(self._sync_broadband_spinboxes)
        # self.maxbroadBox.editingFinished.connect(self.validate_broadband_interval)

        # Store the default values in a dict
        self.defaults = {
            "minfreqnotch": self.minfreqnotchBox.value(),
            "maxfreqnotch": self.maxfreqnotchBox.value(),
            "ordernotch": self.orderNotchBox.value(),
            "minfreqbp": self.minfreqbpBox.value(),
            "maxfreqbp": self.maxfreqbpBox.value(),
            "orderbp": self.orderbpBox.value(),
        }
        print(self.defaults)

        # Set initial state
        self.reset_all_controls()
        [elm.setDisabled(True) for elm in self.element_group]
        self.main_window.selected_files = self.selected_files
        for widget in [self.selectedbandsLabel, self.selectedbandsauxLabel, self.bandLabel, self.bandButton]:
            widget.setVisible(False)


    def reset_all_controls(self):
        """
        This function hides all elements of the data preprocessing groupbox and sets them to their default values.
        It is called:
            - At Analyzer startup.
            - When Preprocess data is unchecked.
            - When the files are deleted (by clicking 'delete' from the 'View list').
        """

        # Hide elements
        for w in [
            self.notchLabel, self.notchCBox, self.notchminLabel, self.minfreqnotchBox, self.notchmaxLabel, self.maxfreqnotchBox, self.winnotchLabel, self.winnotchBox, self.orderNotchLabel, self.orderNotchBox,
            self.bpLabel, self.bpCBox, self.bpminLabel, self.minfreqbpBox, self.bpmaxLabel, self.maxfreqbpBox, self.orderbpLabel, self.orderbpBox, self.winbpLabel, self.winbpBox,
            self.carLabel, self.carCBox, self.notchPlotWidget, self.bandpassPlotWidget, self.bpgroupBox, self.cargroupBox,
            self.notchgroupBox, self.drawnotchButton, self.drawbpButton,
        ]:
            w.setVisible(False)

        # Reset checkboxes
        for box in [self.notchCBox, self.bpCBox, self.carCBox, self.preprocessingButton]: box.setChecked(False)
        [elm.setDisabled(True) for elm in self.element_group]

        # Reset spinboxes
        self.minfreqnotchBox.setValue(self.defaults["minfreqnotch"])
        self.maxfreqnotchBox.setValue(self.defaults["maxfreqnotch"])
        self.orderNotchBox.setValue(self.defaults["ordernotch"])
        self.minfreqbpBox.setValue(self.defaults["minfreqbp"])
        self.maxfreqbpBox.setValue(self.defaults["maxfreqbp"])
        self.orderbpBox.setValue(self.defaults["orderbp"])


    def select_files(self):
        """
            Function to select multiple .rec.bson files from various folders.
                - It stores them in 'self.selected_files'.
                - Updates the label with the number of files.
                - Enables the checkbox for preprocessing.
                - If invalid files are selected, prompts to open the converter.
        """
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select recordings", "", "Recording files (*.bson *.json)"
        )

        if not files:
            return

        # Separate .rec.bson and others
        rec_files = [f for f in files if f.endswith(".rec.bson")]
        to_convert = [f for f in files if not f.endswith(".rec.bson")]

        converted_paths = []
        if to_convert:
            QtWidgets.QMessageBox.information(
                self,
                "Automatic Conversion",
                f"{len(to_convert)} file(s) are not '.rec.bson' and will be automatically converted."
            )

            self.convertLogTextBrowser.clear()
            self.convertLogTextBrowser.setVisible(True)
            self.convertProgressBar.setValue(0)
            self.convertProgressBar.setVisible(True)
            QtWidgets.QApplication.processEvents()

            try:
                # Call converter and get paths of new .rec.bson files
                converted_paths = conversor_to_rec(
                    to_convert,
                    self.convertProgressBar,
                    self.convertLogTextBrowser,
                    return_rec_paths=True
                )

                QtWidgets.QMessageBox.information(
                    self,
                    "Conversion Complete",
                    f"Successfully converted {len(to_convert)} file(s)."
                )
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self, "Conversion Error", f"An error occurred during conversion:\n{str(e)}"
                )
                return

            finally:
                self.convertProgressBar.setVisible(False)
                self.convertLogTextBrowser.setVisible(False)

        # Combine all valid .rec.bson files
        all_rec_files = rec_files + converted_paths

        # Avoid duplicates
        new_files = [f for f in all_rec_files if f not in self.selected_files]
        if not new_files:
            QtWidgets.QMessageBox.information(
                self, "No New Files", "All selected files are already loaded."
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
        self.selectLabel.setText(f"{count} selected files")

        # Sync with main_window
        self.main_window.selected_files = self.selected_files.copy()
        self.main_window.segmentation_widget.reset_segmentation_state()

        if count > 0:
            self.main_window.nextButton.setDisabled(False)
            eeg = components.Recording.load(self.selected_files[0])
            self.main_window.sampling_frequency = eeg.eeg.fs
            self.main_window.num_chann = len(eeg.eeg.channel_set.l_cha)
            self.main_window.segmentation_widget.threschanBox.setMaximum(self.main_window.num_chann)
            [elm.setDisabled(False) for elm in self.element_group]
            self.minbroadBox.setValue(0.5)
            self.maxbroadBox.setValue(self.main_window.sampling_frequency/2)
            self.minfreqbpBox.setValue(0.5)
            self.maxfreqbpBox.setValue(self.main_window.sampling_frequency/2)
            self.main_window.segmentation_widget.update_max_samples()

        else:
            self.main_window.nextButton.setDisabled(True)
            [elm.setDisabled(True) for elm in self.element_group]

    def open_file_list_dialog(self):
        """
            Function that opens the file list dialog, and stores the updated file list
        """
        dialog = FilesListDialog(self.selected_files, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.selected_files = dialog.get_updated_files()
            self.update_select_label()

    def select_and_convert_files(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Select .rcp.bson files to convert",
            "",
            "BSON files (*.bson)"
        )

        if not files:
            return

        valid_files = []
        for file in files:
            if not file.endswith(".rcp.bson"):
                continue
            rec_path = file.replace(".rcp.bson", ".rec.bson")
            if os.path.exists(rec_path):
                result = QtWidgets.QMessageBox.question(
                    self,
                    "File already exists",
                    f"The file '{os.path.basename(rec_path)}' already exists.\nDo you want to overwrite it?",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                )
                if result == QtWidgets.QMessageBox.No:
                    continue
            valid_files.append(file)

        if not valid_files:
            QtWidgets.QMessageBox.information(self, "No Valid Files", "No valid files selected for conversion.")
            return

        self.convertLogTextBrowser.clear()
        self.convertLogTextBrowser.setVisible(True)
        self.convertProgressBar.setValue(0)
        self.convertProgressBar.setVisible(True)
        QtWidgets.QApplication.processEvents()

        try:
            conversor_to_rec(valid_files, self.convertProgressBar, self.convertLogTextBrowser)
            QtWidgets.QMessageBox.information(
                self,
                "Conversion Complete",
                f"Successfully converted {len(valid_files)} file(s)."
            )

            rec_files = [f.replace(".rcp.bson", ".rec.bson") for f in valid_files]
            for f in rec_files:
                if f not in self.selected_files:
                    self.selected_files.append(f)
            self.update_select_label()

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Conversion Error",
                f"An error occurred:\n{str(e)}"
            )
        finally:
            self.convertProgressBar.setVisible(False)
            self.convertLogTextBrowser.setVisible(False)

    def toggle_preprocessing_group(self):
        """
            This function shows or hides the preprocessing controls depending on whether the user chooses to apply them
            or not. Additionally, it also enables the Next button in the main window.
        """

        if not self.preprocessingButton.isChecked():
            self.reset_all_controls()
            return
        else: # Show all the checkboxes, but keep their parameters hidden

            self.cargroupBox.setVisible(True)
            self.bpgroupBox.setVisible(True)
            self.notchgroupBox.setVisible(True)

            pairs = [
                (self.notchLabel, self.notchCBox),
                (self.bpLabel, self.bpCBox),
                (self.carLabel, self.carCBox),
            ]
            for label, checkbox in pairs:
                label.setVisible(True)
                checkbox.setVisible(True)


    def toggle_notch_controls(self, checked):
        """
            Shows (or hides) the parameters associated with 'notch_filter' when its main checkbox is checked (or
            unchecked).
        """

        # Show (or hide)
        self.notchPlotWidget.setVisible(checked)
        self.notchminLabel.setVisible(checked)
        self.minfreqnotchBox.setVisible(checked)
        self.notchmaxLabel.setVisible(checked)
        self.maxfreqnotchBox.setVisible(checked)
        self.orderNotchLabel.setVisible(checked)
        self.orderNotchBox.setVisible(checked)
        self.drawnotchButton.setVisible(checked)
        self.winnotchBox.setVisible(checked)
        self.winnotchLabel.setVisible(checked)

        # Reset default values
        if not checked:
            self.minfreqnotchBox.setValue(self.defaults["minfreqnotch"])
            self.maxfreqnotchBox.setValue(self.defaults["maxfreqnotch"])
            self.orderNotchBox.setValue(self.defaults["ordernotch"])
            self.winnotchBox.setCurrentIndex(9)


    def toggle_bandpass_controls(self, checked):
        """
            Shows (or hides) the parameters associated with 'bandpass_filter' when its main checkbox is checked
            (or unchecked).
        """

        # Show (or hide)
        self.bandpassPlotWidget.setVisible(checked)
        self.bpminLabel.setVisible(checked)
        self.minfreqbpBox.setVisible(checked)
        self.bpmaxLabel.setVisible(checked)
        self.maxfreqbpBox.setVisible(checked)
        self.orderbpLabel.setVisible(checked)
        self.orderbpBox.setVisible(checked)
        self.drawbpButton.setVisible(checked)
        self.winbpLabel.setVisible(checked)
        self.winbpBox.setVisible(checked)
        # self.maxbroadBox.setValue(self.maxfreqbpBox.value())

        if checked:
            self.minfreqbpBox.setValue(self.defaults["minfreqbp"])
            self.maxfreqbpBox.setValue(self.defaults["maxfreqbp"])
            self.orderbpBox.setValue(self.defaults["orderbp"])
            self.maxbroadBox.setValue(self.maxfreqbpBox.value())

        # Reset default values
        if not checked:
            self.minfreqbpBox.setValue(self.defaults["minfreqbp"])
            self.maxfreqbpBox.setValue(self.defaults["maxfreqbp"])
            self.orderbpBox.setValue(self.defaults["orderbp"])
            self.maxbroadBox.setValue(self.main_window.sampling_frequency/2)

    def validate_filter_bounds(self, filter_type):
        """
            Function that validates the filter bounds (Low freq < high freq)
        """

        if filter_type == 'bandpass':
            min_val = self.minfreqbpBox.value()
            max_val = self.maxfreqbpBox.value()
        else:
            min_val = self.minfreqnotchBox.value()
            max_val = self.maxfreqnotchBox.value()

        if max_val > (self.main_window.sampling_frequency/2):
            QMessageBox.warning(
                self,
                f"Invalid values for {filter_type} filter.",
                f"For {filter_type} filtering, <b>max</b> frequency {max_val} must be lower than <b>fs</b> {self.main_window.sampling_frequency}.",
            )
            if filter_type == 'bandpass':
                self.minfreqbpBox.setValue(self.defaults["minfreqbp"])
                self.maxfreqbpBox.setValue(self.defaults["maxfreqbp"])
            else:
                self.minfreqnotchBox.setValue(self.defaults["minfreqnotch"])
                self.maxfreqnotchBox.setValue(self.defaults["maxfreqnotch"])
            return False

        if max_val <= min_val:
            QMessageBox.warning(
                self,
                f"Invalid values for {filter_type} filter.",
                f"For {filter_type} filtering, <b>max</b> frequency {max_val} must be greater than <b>min</b> {min_val}."
            )

            if filter_type == 'bandpass':
                self.minfreqbpBox.setValue(self.defaults["minfreqbp"])
                self.maxfreqbpBox.setValue(self.defaults["maxfreqbp"])
            else:
                self.minfreqnotchBox.setValue(self.defaults["minfreqnotch"])
                self.maxfreqnotchBox.setValue(self.defaults["maxfreqnotch"])

            return False
        else:
            return True

    def update_filter_plot(self, filter_type):
        """
            Function that plots the filter
        """
        if filter_type == 'bandpass':
            if not self.bpCBox.isChecked():
                self.bandpassCanvas.ax.clear()
                self.bandpassCanvas.draw()
                return
            low = self.minfreqbpBox.value()
            high = self.maxfreqbpBox.value() - 1e-6
            numtaps = self.orderbpBox.value()
            win = self.winbpBox.currentText()

        else:  # notch
            if not self.notchCBox.isChecked():
                self.notchCanvas.ax.clear()
                self.notchCanvas.draw()
                return
            low = self.minfreqnotchBox.value()
            high = self.maxfreqnotchBox.value()
            numtaps = self.orderNotchBox.value()
            win = self.winnotchBox.currentText()

            if numtaps % 2 == 0:
                numtaps += 1
                self.orderNotchBox.setValue(numtaps)

        if not self.validate_filter_bounds(filter_type):
            return

        fs = self.main_window.sampling_frequency
        b = firwin(
            numtaps,
            [low, high],
            pass_zero=(filter_type == 'notch'),
            fs=fs,
            window=win
        )
        w, h = freqz(b, worN=1024, fs=fs)

        # Create the plot
        canvas = self.bandpassCanvas if filter_type == 'bandpass' else self.notchCanvas
        canvas.ax.clear()
        canvas.ax.plot(w, 20 * np.log10(np.maximum(abs(h), 1e-6)), color="#ab47bc", linewidth=2.0)
        canvas.ax.set_title(f"{filter_type} Filter", fontsize=10, color="#000000")
        canvas.ax.set_ylabel("Gain (dB)", fontsize=9, color="#000000")
        canvas.ax.set_xlim([0, fs / 2])
        canvas.ax.grid(False)
        canvas.ax.tick_params(labelsize=8, colors="#000000")
        canvas.fig.tight_layout()
        canvas.draw()

    # def validate_broadband_interval(self):
    #     """
    #         Function that validates the broadband bounds (Low freq < high freq)
    #     """
    #
    #     start = self.minbroadBox.value()
    #     end = self.maxbroadBox.value()
    #     if end <= start:
    #         # Block the signals to avoid loops
    #         self.minbroadBox.blockSignals(True)
    #         self.maxbroadBox.blockSignals(True)
    #
    #         QtWidgets.QMessageBox.warning(
    #             self,
    #             "Invalid Broadband range",
    #             "Max. frequency must be higher than min. frequency."
    #         )
    #
    #         self.minbroadBox.setValue(getattr(self, "default_min_broad", 0.5))
    #         self.maxbroadBox.setValue(getattr(self, "default_max_broad", 70))
    #
    #         # Unlock signals
    #         self.minbroadBox.blockSignals(False)
    #         self.maxbroadBox.blockSignals(False)


    # def set_defaults_broadband(self, params):
    #     """
    #         Set default values for the broadband interval.
    #     """
    #     if not self.initialized or self._params_changed(params):
    #         if params.get("bandpass"):
    #             self.default_min_broad = params.get("bp_min", 0)
    #             self.default_max_broad = params.get("bp_max", 70)
    #         else:
    #             self.default_min_broad = 0.5
    #             self.default_max_broad = self.main_window.sampling_frequency/2  # TO DO: use fs/2
    #
    #         self.minbroadBox.setValue(self.default_min_broad)
    #         self.maxbroadBox.setValue(self.default_max_broad)
    #
    #         self.last_params = dict(params)
    #         self.initialized = True

    def _params_changed(self, new_params):
        """
            Checks if some relevant parameters have changed.
        """
        # If they have not been stored, they have changed
        if self.last_params is None:
            return True
        # Check for changes only in relevant keys
        keys_to_check = ["bandpass", "bp_min", "bp_max"]
        return any(self.last_params.get(k) != new_params.get(k) for k in keys_to_check)


    def toggle_bands_segmentation(self):
        """
            Function to display the data related to frequency bands when the corresponding checkbox is checked to
            indicate that band segmentation should be performed. If the checkbox is unchecked, the data is hidden.
        """
        visible = self.bandCBox.isChecked()
        for widget in [self.selectedbandsLabel, self.selectedbandsauxLabel, self.bandLabel, self.bandButton]:
            widget.setVisible(visible)
        self.bandLabel.setText("None")
        self.band_editor = None
        self.band_config_changed.emit()

    def disable_bandsegmentation_on_bp_change(self):
        if self.bandCBox.isChecked():
            self.bandCBox.setChecked(False)

    def open_band_editor(self, band_type):
        """
            Opens the band editor
        """
        # If it is not initialized, do it
        if self.band_editor is None:
            self.band_editor = BandTable(
                preprocessing_widget=self,
                band_type=band_type,
                min_broad=self.minbroadBox.value(),
                max_broad=self.maxbroadBox.value()
            )
            self.band_editor.setModal(True)  # Disables the MainWindow without closing or breaking inheritance.
            self.band_editor.show()
        else:
            # Before showing the band editor, update the broadband range
            self.band_editor.sync_broadband_range(
                self.minbroadBox.value(),
                self.maxbroadBox.value()
            )
        self.band_editor.show()

    def update_band_label(self, band_type, bands):
        """
            Updates the labels with the names of the selected bands
        """
        self.selected_bands_by_type = getattr(self, "selected_bands_by_type", {})
        self.selected_bands_by_type[band_type] = bands

        label = self.findChild(QtWidgets.QLabel, f"bandLabel")
        if label:
            if bands:
                names = [f"{b['name']} ({b['min']}–{b['max']} Hz)" for b in bands]
                label.setText(", ".join(names))
            else:
                label.setText("None")

        self.band_config_changed.emit()

    # def _sync_broadband_spinboxes(self):
    #     if self.band_editor:
    #         self.band_editor.sync_broadband_range(
    #             self.minbroadBox.value(),
    #             self.maxbroadBox.value()
    #         )

    def update_broadband_spinboxes(self, min_val, max_val):
        self.minbroadBox.blockSignals(True)
        self.maxbroadBox.blockSignals(True)
        self.minbroadBox.setValue(min_val)
        self.maxbroadBox.setValue(max_val)
        self.minbroadBox.blockSignals(False)
        self.maxbroadBox.blockSignals(False)

    def show_freq_content_dialog(self):
        QtWidgets.QMessageBox.information(self, "Data frequency content",
                                          "To calculate many parameters in your data, it is necessary to know the "
                                          "frequency limits. By default, this range is set between 0.5 and half the "
                                          "sampling frequency, but it will be updated if you bandpass filter the "
                                          "signal.")

    def get_preprocessing_config(self):
        """
            Function that creates a dictionary with preprocessing configurations.
        """
        config = {
            "fs": self.main_window.sampling_frequency,
            "band_segmentation": True if self.bandCBox.isChecked() else None,
            "broadband_min": self.minbroadBox.value(),
            "broadband_max": self.maxbroadBox.value(),
            "selected_bands": (
                None
                if (not self.bandCBox.isChecked() or (
                    len(self.selected_bands_by_type.get("segmentation", [])) == 1 and
                    str(self.selected_bands_by_type.get("segmentation", [])[0].get("name","")).lower() == "broadband"
                ))
                else self.selected_bands_by_type.get("segmentation", [])
            ),
            "selected_files": self.selected_files if self.selected_files else None,
            "apply_preprocessing": True if self.preprocessingButton.isChecked() else None,

            "notch": self.notchCBox.isChecked() if self.notchCBox else None,
            "notch_min": self.minfreqnotchBox.value() if self.notchCBox.isChecked() else None,
            "notch_max": self.maxfreqnotchBox.value() if self.notchCBox.isChecked() else None,
            "notch_order": self.orderNotchBox.value() if self.notchCBox.isChecked() else None,
            "notch_win": self.winnotchBox.currentText() if self.notchCBox.isChecked() else None,

            "bandpass": self.bpCBox.isChecked() if self.bpCBox else None,
            "bp_min": self.minfreqbpBox.value() if self.bpCBox.isChecked() else None,
            "bp_max": self.maxfreqbpBox.value() if self.bpCBox.isChecked() else None,
            "bp_order": self.orderbpBox.value() if self.bpCBox.isChecked() else None,
            "bp_win": self.winbpBox.currentText() if self.bpCBox.isChecked() else None,

            "car": self.carCBox.isChecked() if self.carCBox else None,
        }
        return config
