import sys
from PyQt5 import QtWidgets, uic, QtGui
from PyQt5.QtWidgets import QApplication
from preprocessing import PreprocessingWidget
from segmentation import SegmentationWidget
from parameters import ParametersWidget
from download import DownloadWidget

class GradientTitleWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(56)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        font = QtGui.QFont("Arial", 36, QtGui.QFont.Bold)
        painter.setFont(font)

        text = "MEDUSA©-Analyzer"
        fm = QtGui.QFontMetrics(font)
        text_width = fm.width(text)

        x = (self.width() - text_width) // 2
        y = (self.height()  + fm.ascent() - fm.descent()) // 2

        gradient = QtGui.QLinearGradient(x, 0, x + text_width, 0)
        gradient.setColorAt(0.0, QtGui.QColor("#6a0dad"))   # Morado
        gradient.setColorAt(1.0, QtGui.QColor("#ec407a"))   # Rosa

        brush = QtGui.QBrush(gradient)
        painter.setPen(QtGui.QPen(brush, 0))
        painter.drawText(x, y, text)

class MainWindow(QtWidgets.QMainWindow):
    """
    Main application window. Manages navigation through the main stages of the workflow:
    Preprocessing, Segmentation, Signal Analysis, and Downloads.
    """

    def __init__(self):
        super().__init__()
        uic.loadUi("main_window.ui", self)
        self.selected_files = []

        self.title_widget = GradientTitleWidget(self)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.title_widget)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(0)
        self.titleWidget = self.findChild(QtWidgets.QWidget, "titleWidget")
        self.titleWidget.setLayout(layout)

        # --- UI Components ---
        self.stackedWidget = self.findChild(QtWidgets.QStackedWidget, "stackedWidget")
        self.nextButton = self.findChild(QtWidgets.QPushButton, "nextButton")
        self.backButton = self.findChild(QtWidgets.QPushButton, "backButton")
        self.progressLabel = self.findChild(QtWidgets.QLabel, "progressLabel")
        self.stepBar0 = self.findChild(QtWidgets.QWidget, "stepBar0")
        self.stepBar1 = self.findChild(QtWidgets.QWidget, "stepBar1")
        self.stepBar2 = self.findChild(QtWidgets.QWidget, "stepBar2")
        self.stepBar3 = self.findChild(QtWidgets.QWidget, "stepBar3")
        self.toolBox = self.findChild(QtWidgets.QToolBox, "toolBox")
        self.bandSegmentationPage = self.findChild(QtWidgets.QWidget, "bandSegmentationPage")

        # --- Setup Navigation Buttons ---
        self.nextButton.setDisabled(True)  # 'Next' is disabled until valid input is provided
        self.nextButton.clicked.connect(self.go_next)
        self.backButton.clicked.connect(self.go_back)

        # --- Initialize Step Info ---
        self.total_steps = self.stackedWidget.count()
        self.step_names = ["Preprocessing", "Segmentation", "Signal Analysis", "Downloads"]

        # --- Insert Workflow Widgets into StackedWidget ---
        self.preproc_widget = PreprocessingWidget(self)
        self.stackedWidget.insertWidget(0, self.preproc_widget)

        self.segmentation_widget = SegmentationWidget(self)
        self.segmentation_widget.hide_all_param_widgets()
        self.stackedWidget.insertWidget(1, self.segmentation_widget)

        self.parameters_widget = ParametersWidget(self)
        self.stackedWidget.insertWidget(2, self.parameters_widget)

        self.download_widget = DownloadWidget(self)
        self.stackedWidget.insertWidget(3, self.download_widget)

        # --- Initial State ---
        self.stackedWidget.setCurrentIndex(0)  # Start with the Preprocessing tab
        self.stackedWidget.currentChanged.connect(self.on_tab_changed)
        self.update_ui()


    def go_next(self):
        idx = self.stackedWidget.currentIndex()

        if idx == 0 and not self.validate_preprocessing(): return
        if idx == 1 and not self.validate_segmentation(): return
        if idx == 2 and not self.validate_parameters(): return

        if idx < self.total_steps - 1:
            self.stackedWidget.setCurrentIndex(idx + 1)
            self.update_ui()
        else:
            self.close()

    def go_back(self):
        idx = self.stackedWidget.currentIndex()
        if idx > 0:
            self.stackedWidget.setCurrentIndex(idx - 1)
            self.update_ui()

    def update_ui(self):
        """
        Updates the user interface based on the current step in the workflow.

        This includes:
        - Setting the step label with the current step number and name.
        - Updating the visual progress bar.
        - Controlling visibility of the Back button (hidden on the first step).
        - Updating the Next button text (changes to 'Finish' on the last step).
        """
        idx = self.stackedWidget.currentIndex()
        self.progressLabel.setText(f"Step {idx + 1} of {self.total_steps}: {self.step_names[idx]}")
        self.update_progress_bar(idx)
        self.backButton.setVisible(idx > 0)
        self.nextButton.setText("Finish" if idx == self.total_steps - 1 else "Next")

    def update_progress_bar(self, idx):
        bars = [self.stepBar0, self.stepBar1, self.stepBar2, self.stepBar3]
        colors = ["#FF8A5C", "#F63553", "#6234BD", "#3117A4"]
        for i, bar in enumerate(bars):
            bar.setStyleSheet(f"background-color: {colors[i] if i <= idx else 'lightgray'}")

    def on_tab_changed(self, index):
        '''
        This function ensures that when the user navigates backward through the tabs after interacting with them,
        their previous selections and entered data are preserved. It maintains the consistency of the user interface
        in accordance with the user's interactions.
        '''
        self.update_ui()

        if index == 0:
            print('Hola')
        # if index == 0 and (self.preproc_widget.yesRButton.isChecked() or self.preproc_widget.noRButton.isChecked()):
        #     self.nextButton.setDisabled(False)

        elif index == 1 and (not self.segmentation_widget.conditions or not self.segmentation_widget.events):
            if self.selected_files:
                self.segmentation_widget.load_and_display_events_from_file(self.selected_files[0])

        elif index == 2:
            toolbox, page = self.parameters_widget.toolBox, self.parameters_widget.bandSegmentationPage
            if toolbox and page:
                idx = toolbox.indexOf(page)
                if idx != -1:
                    toolbox.setCurrentIndex(idx)
            self.nextButton.setEnabled(True)

        elif index == 3:
            self.nextButton.setEnabled(False)
        else:
            self.nextButton.setEnabled(True)

    def validate_preprocessing(self):
        """
            Validates user selections in the Preprocessing step before proceeding.

            Checks:
            - If preprocessing is enabled, at least one step (Notch, BP, CAR) must be selected.
            - Bandpass filter parameters must have valid min < max values.

            Side Effects:
            - Displays warning dialogs on validation failure.
            - Resets invalid input fields to safe defaults.
            - Loads events for the segmentation step if validation passes.
            - Passes the preprocessing configuration to the Parameters widget.

            Returns:
                bool: True if all validations pass, False otherwise.
            """
        pw = self.preproc_widget
        if pw.preprocessingButton.isChecked() and not (
                pw.notchCBox.isChecked() or pw.bpCBox.isChecked() or pw.carCBox.isChecked()):
            self._warn("Processing Pipeline Required",
                       "Please select at least one preprocessing step before continuing.")
            return False

        if pw.bpCBox.isChecked() and pw.minfreqbpBox.value() >= pw.maxfreqbpBox.value():
            self._warn("Invalid Bandpass Filter Configuration",
                       f"The <b>maximum</b> frequency ({pw.maxfreqbpBox.value()}) must be greater than "
                       f"the <b>minimum</b> frequency ({pw.minfreqbpBox.value()}).")
            pw.minfreqbpBox.setValue(pw.defaults["minfreqbp"])
            pw.maxfreqbpBox.setValue(pw.defaults["maxfreqbp"])
            return False

        if pw.notchCBox.isChecked() and pw.minfreqnotchBox.value() >= pw.maxfreqnotchBox.value():
            self._warn("Invalid Notch Filter Configuration",
                       f"The <b>maximum</b> frequency ({pw.maxfreqnotchBox.value()}) must be greater than "
                       f"the <b>minimum</b> frequency ({pw.minfreqnotchBox.value()}).")
            pw.minfreqnotchBox.setValue(pw.defaults["minfreqnotch"])
            pw.maxfreqnotchBox.setValue(pw.defaults["maxfreqnotch"])
            return False

        self.segmentation_widget.load_and_display_events_from_file(self.selected_files[0])
        config = pw.get_preprocessing_config()
        print(config)
        self.parameters_widget.set_defaults_from_preprocessing(config)
        return True

    def validate_segmentation(self):
        """
            Validates user selections in the Segmentation step before proceeding.

            Checks:
            - At least one condition must be selected when condition-based segmentation is active.
            - If normalization is enabled, at least one type (z-score or DC) must be selected.
            - Event-related windows (analysis and baseline) must have valid min < max values.
            - At least one condition and one event must be selected if event-based segmentation is active.

            Side Effects:
            - Displays warning dialogs on validation failure.
            - Resets invalid input fields to default safe values.
            - Prints the current segmentation configuration.

            Returns:
                bool: True if all validations pass, False otherwise.
            """
        sw = self.segmentation_widget

        if not sw.conditionRButton.isChecked() and not sw.eventRButton.isChecked():
            self._warn("Segmentation Selection Required", "Please select at least one segmentation type before proceeding.")
            return False
        if sw.conditionRButton.isChecked() and not sw.conditionList.selectionModel().selectedIndexes():
            self._warn("Condition Selection Required", "Please select at least one condition before proceeding.")
            return False

        if sw.normCBox.isChecked() and not (sw.zscoreRButton.isChecked() or sw.dcRButton.isChecked()):
            self._warn("Normalization Selection Required",
                       "Please select at least one normalization type before proceeding.")
            return False

        if sw.eventRButton.isChecked():
            if sw.winBox_1.value() >= sw.winBox_2.value():
                self._warn("Invalid Window Interval",
                           f"The <b>maximum</b> value ({sw.winBox_2.value()}) must be greater than "
                           f"the <b>minimum</b> value ({sw.winBox_1.value()}).")
                sw.winBox_1.setValue(0)
                sw.winBox_2.setValue(1)
                return False

            if sw.normCBox.isChecked() and sw.baselineCBox_1.value() >= sw.baselineCBox_2.value():
                self._warn("Invalid Baseline Window Interval",
                           f"The <b>maximum</b> value ({sw.baselineCBox_2.value()}) must be greater than "
                           f"the <b>minimum</b> value ({sw.baselineCBox_1.value()}).")
                sw.baselineCBox_1.setValue(0)
                sw.baselineCBox_2.setValue(1)
                return False

            if (not sw.conditionList.selectionModel().selectedIndexes() or
                    not sw.eventList.selectionModel().selectedIndexes()):
                self._warn("Incomplete Selection", "Please select at least one condition and one event to continue.")
                return False

        print(sw.get_segmentation_config())
        return True

    def validate_parameters(self):
        """
            Validates user selections in the Parameters step before proceeding.

            Checks:
            - Broadband range must have valid min < max values.
            - If specific features are enabled (band segmentation, relative/absolute power, etc.),
              corresponding frequency bands must be defined.
            - Frequency bands must lie within the defined broadband range.
            - If relative/absolute power is enabled but PSD is not, warn that default PSD settings will be used.


            Side Effects:
            - Displays warning dialogs on validation failure.
            - Resets broadband inputs to default values if invalid.
            - Updates 'Broadband' band values dynamically.
            - Prints the final parameter configuration for debugging.

            Returns:
                bool: True if all validations pass, False otherwise.
            """
        pw = self.parameters_widget
        min_b, max_b = pw.minbroadBox.value(), pw.maxbroadBox.value()

        if min_b >= max_b:
            self._warn("Invalid Broadband Range", "The maximum frequency must be greater than the minimum frequency.")
            pw.minbroadBox.setValue(getattr(pw, "default_min_broad", 0.5))
            pw.maxbroadBox.setValue(getattr(pw, "default_max_broad", 70))
            return False

        checks = [
            (pw.bandCBox.isChecked() and pw.bandLabel.text() == "None", "Band Segmentation Required",
             "Please define at least one frequency band to enable band-based segmentation."),
            (pw.rpCBox.isChecked() and pw.rpLabel.text() == "None", "Relative Power Configuration Missing",
             "Please define at least one frequency band to enable relative power analysis."),
            (pw.apCBox.isChecked() and pw.apLabel.text() == "None", "Absolute Power Configuration Missing",
             "Please define at least one frequency band to enable absolute power analysis."),
            (pw.mfCBox.isChecked() and pw.mfLabel.text() == "None", "Median Frequency Configuration Missing",
             "Please define at least one target band to enable median frequency analysis."),
            (pw.seCBox.isChecked() and pw.seLabel.text() == "None", "Spectral Entropy Configuration Missing",
             "Please define at least one target band to enable spectral entropy analysis."),
        ]
        for cond, title, msg in checks:
            if cond:
                self._warn(title, msg)
                return False

        if ((pw.rpCBox.isChecked() or pw.apCBox.isChecked() or pw.mfCBox.isChecked() or pw.seCBox.isChecked())
                and not pw.psdCBox.isChecked()):
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "PSD Configuration Notice",
                "Spectral analysis requires the power spectral density (PSD).\n\n"
                "Since PSD is not enabled, the analysis will default to the following PSD settings:\n"
                "- 80% of the signal segments will be used to compute the FFT,\n"
                "- 50% overlap will be applied using Welch's method,\n"
                "- A 'boxcar' window will be used.\n\n"
                "You may enable PSD manually to customize these settings."
            )

        config = pw.get_parameters_config()
        band_checks = [("selected_bands", pw.bandCBox.isChecked(), "Frequency Bands"),
            ("selected_rp_bands", pw.rpCBox.isChecked(), "Relative Power"),]
        for key, enabled, label in band_checks:
            if not enabled:
                continue
            for band in config.get(key, []):
                if band.get("name") == "Broadband":
                    band["min"], band["max"] = min_b, max_b
                if band.get("min", 0) < min_b or band.get("max", 0) > max_b:
                    self._warn("Frequency Band Out of Range",
                               f"The band <b>{band.get('name', 'Unnamed')}</b> in the '{label} Table' "
                               f"(range: {band.get('min', 0)}-{band.get('max', 0)} Hz) exceeds the allowed Broadband limits ({min_b}-{max_b} Hz).")
                    return False
        print(config)
        return True

    def validate_download_step(self, success: bool):
        current_widget = self.stackedWidget.currentWidget()
        if not isinstance(current_widget, DownloadWidget):
            return

        if success:
            QtWidgets.QMessageBox.information(self, "Download Complete", "Files downloaded successfully.")
            self.nextButton.setEnabled(True)
        else:
            print("Pipeline failed. nextButton will remain disabled.")
            self.nextButton.setEnabled(False)

    def _warn(self, title, message):
        QtWidgets.QMessageBox.warning(self, title, message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())