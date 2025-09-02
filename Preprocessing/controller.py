import numpy as np
from PyQt5.uic.Compiler.qtproxies import QtWidgets
from scipy.signal import firwin, freqz
from bands_table import BandTable # todo - mover a la carpera eeg_params

class EEGParamsPreprocessingController:
    def __init__(self, ui, main_window):
        self.view = ui
        self.main_window = main_window

        # Data preprocessing
        self.reset_all_controls()
        self.view.preprocessingButton.toggled.connect(self.toggle_preprocessing_group)
        # Broadband
        self.view.minbroadBox.valueChanged.connect(self.disable_band_segmentation_on_bp_change)
        self.view.maxbroadBox.valueChanged.connect(self.disable_band_segmentation_on_bp_change)
        # Notch
        self.view.notchCBox.toggled.connect(self.toggle_notch_controls)
        self.view.notchCBox.toggled.connect(lambda: self.update_filter_plot('notch'))
        self.view.drawnotchButton.clicked.connect(lambda: self.update_filter_plot('notch'))
        bg_color = self.view.palette().color(self.view.backgroundRole()).name()
        self.view.notchCanvas.fig.patch.set_facecolor(bg_color)
        self.view.notchCanvas.ax.set_facecolor(bg_color)
        # Bandpass
        self.view.bpCBox.toggled.connect(self.toggle_bandpass_controls)
        self.view.bpCBox.toggled.connect(lambda: self.update_filter_plot('bandpass'))
        self.view.drawbpButton.clicked.connect(lambda: self.update_filter_plot('bandpass'))
        self.view.bandpassCanvas.fig.patch.set_facecolor(bg_color)
        self.view.bandpassCanvas.ax.set_facecolor(bg_color)
        self.view.minfreqbpBox.valueChanged.connect(lambda: self.view.minbroadBox.setValue(self.view.minfreqbpBox.value()))
        self.view.maxfreqbpBox.valueChanged.connect(lambda: self.view.maxbroadBox.setValue(self.view.maxfreqbpBox.value()))
        self.view.minfreqbpBox.valueChanged.connect(self.disable_band_segmentation_on_bp_change)
        self.view.maxfreqbpBox.valueChanged.connect(self.disable_band_segmentation_on_bp_change)

        # Band segmentation
        self.view.bandCBox.toggled.connect(self.toggle_bands_segmentation)
        self.view.bandButton.clicked.connect(lambda: self.open_band_editor("segmentation"))

    def reset_all_controls(self):
        """
        Hides all elements of the data preprocessing groupbox and resets them to defaults.
        Called at:
            - Analyzer startup
            - When 'Preprocess data' is unchecked
            - When files are deleted #TODO
        """

        # Widgets to hide
        widgets_to_hide = [
            self.view.notchfilterLabel, self.view.notchCBox, self.view.notchminLabel, self.view.minfreqnotchBox,
            self.view.notchmaxLabel, self.view.maxfreqnotchBox, self.view.winnotchLabel, self.view.winnotchBox,
            self.view.orderNotchLabel, self.view.orderNotchBox,
            self.view.bpLabel, self.view.bpCBox, self.view.bpminfreqLabel, self.view.minfreqbpBox,
            self.view.bpmaxfreqLabel, self.view.maxfreqbpBox, self.view.orderbpLabel, self.view.orderbpBox,
            self.view.winbpLabel, self.view.winbpBox,
            self.view.carLabel, self.view.carCBox,
            self.view.notchPlotWidget, self.view.bandpassPlotWidget,
            self.view.bpgroupBox, self.view.cargroupBox, self.view.notchgroupBox,
            self.view.drawnotchButton, self.view.drawbpButton,
        ]
        for w in widgets_to_hide:
            w.setVisible(False)

        # Reset checkboxes
        for box in (self.view.notchCBox, self.view.bpCBox, self.view.carCBox, self.view.preprocessingButton):
            box.setChecked(False)

        # Disable grouped elements
        for elm in self.view.element_group:
            elm.setDisabled(True)

        # Reset spinboxes using defaults
        spinbox_defaults = {
            self.view.minfreqnotchBox: "minfreqnotch",
            self.view.maxfreqnotchBox: "maxfreqnotch",
            self.view.orderNotchBox: "ordernotch",
            self.view.minfreqbpBox: "minfreqbp",
            self.view.maxfreqbpBox: "maxfreqbp",
            self.view.orderbpBox: "orderbp",
        }
        for box, key in spinbox_defaults.items():
            box.setValue(self.view.defaults[key])

    def toggle_preprocessing_group(self):
        """
            This function shows or hides the preprocessing controls depending on whether the user chooses to apply them
            or not.
        """

        if not self.view.preprocessingButton.isChecked():
            self.view.reset_all_controls()
            return

        else: # Show all the checkboxes, but keep their parameters hidden
            self.view.cargroupBox.setVisible(True)
            self.view.bpgroupBox.setVisible(True)
            self.view.notchgroupBox.setVisible(True)

            pairs = [
                (self.view.notchfilterLabel, self.view.notchCBox),
                (self.view.bpLabel, self.view.bpCBox),
                (self.view.carLabel, self.view.carCBox),
            ]
            for label, checkbox in pairs:
                label.setVisible(True)
                checkbox.setVisible(True)

    def disable_band_segmentation_on_bp_change(self):
        if self.view.bandCBox.isChecked():
            self.view.bandCBox.setChecked(False)

    def toggle_notch_controls(self, checked):
        """
            Shows (or hides) the parameters associated with 'notch_filter' when its main checkbox is checked (or
            unchecked).
        """

        # Show (or hide)
        self.view.notchPlotWidget.setVisible(checked)
        self.view.notchminLabel.setVisible(checked)
        self.view.minfreqnotchBox.setVisible(checked)
        self.view.notchmaxLabel.setVisible(checked)
        self.view.maxfreqnotchBox.setVisible(checked)
        self.view.orderNotchLabel.setVisible(checked)
        self.view.orderNotchBox.setVisible(checked)
        self.view.drawnotchButton.setVisible(checked)
        self.view.winnotchBox.setVisible(checked)
        self.view.winnotchLabel.setVisible(checked)

        # Reset default values
        if not checked:
            self.view.minfreqnotchBox.setValue(self.view.defaults["minfreqnotch"])
            self.view.maxfreqnotchBox.setValue(self.view.defaults["maxfreqnotch"])
            self.view.orderNotchBox.setValue(self.view.defaults["ordernotch"])
            self.view.winnotchBox.setCurrentIndex(9)

    def toggle_bandpass_controls(self, checked):
        """
            Shows (or hides) the parameters associated with 'bandpass_filter' when its main checkbox is checked
            (or unchecked).
        """

        # Show (or hide)
        self.view.bandpassPlotWidget.setVisible(checked)
        self.view.bpminfreqLabel.setVisible(checked)
        self.view.minfreqbpBox.setVisible(checked)
        self.view.bpmaxfreqLabel.setVisible(checked)
        self.view.maxfreqbpBox.setVisible(checked)
        self.view.orderbpLabel.setVisible(checked)
        self.view.orderbpBox.setVisible(checked)
        self.view.drawbpButton.setVisible(checked)
        self.view.winbpLabel.setVisible(checked)
        self.view.winbpBox.setVisible(checked)

        # if checked: todo - sobra?
        #     self.view.minfreqbpBox.setValue(self.view.defaults["minfreqbp"])
        #     self.view.maxfreqbpBox.setValue(self.view.defaults["maxfreqbp"])
        #     self.view.orderbpBox.setValue(self.view.defaults["orderbp"])
        #     self.view.maxbroadBox.setValue(self.view.maxfreqbpBox.value())

        # Reset default values
        if not checked:
            self.view.minfreqbpBox.setValue(self.view.defaults["minfreqbp"])
            self.view.maxfreqbpBox.setValue(self.view.defaults["maxfreqbp"])
            self.view.orderbpBox.setValue(self.view.defaults["orderbp"])
            self.view.maxbroadBox.setValue(self.view.main_window.sampling_frequency/2)

    def validate_filter_bounds(self, filter_type):
        """
            Function that validates the filter bounds (Low freq < high freq)
        """

        if filter_type == 'bandpass':
            min_val = self.view.minfreqbpBox.value()
            max_val = self.view.maxfreqbpBox.value()
        else:
            min_val = self.view.minfreqnotchBox.value()
            max_val = self.view.maxfreqnotchBox.value()

        if max_val <= min_val:
            QtWidgets.QMessageBox.warning(
                self.view,
                f"Invalid values for {filter_type} filter.",
                f"For {filter_type} filtering, <b>max</b> frequency {max_val} must be greater than <b>min</b> {min_val}."
            )

            if filter_type == 'bandpass':
                self.view.minfreqbpBox.setValue(self.view.defaults["minfreqbp"])
                self.view.maxfreqbpBox.setValue(self.view.defaults["maxfreqbp"])
            else:
                self.view.minfreqnotchBox.setValue(self.view.defaults["minfreqnotch"])
                self.view.maxfreqnotchBox.setValue(self.view.defaults["maxfreqnotch"])

            return False
        else:
            return True

    def update_filter_plot(self, filter_type):
        """
            Function that plots the filter
        """
        if filter_type == 'bandpass':
            if not self.view.bpCBox.isChecked():
                self.view.bandpassCanvas.ax.clear()
                self.view.bandpassCanvas.draw()
                return
            low = self.view.minfreqbpBox.value()
            high = self.view.maxfreqbpBox.value() - 1e-6
            numtaps = self.view.orderbpBox.value()
            win = self.view.winbpBox.currentText()

        else:  # notch
            if not self.view.notchCBox.isChecked():
                self.view.notchCanvas.ax.clear()
                self.view.notchCanvas.draw()
                return
            low = self.view.minfreqnotchBox.value()
            high = self.view.maxfreqnotchBox.value()
            numtaps = self.view.orderNotchBox.value()
            win = self.view.winnotchBox.currentText()

            if numtaps % 2 == 0:
                numtaps += 1
                self.view.orderNotchBox.setValue(numtaps)

        if not self.validate_filter_bounds(filter_type):
            return

        fs = 256
        # fs = self.main_window.sampling_frequency # todo - meter en self.main_window
        b = firwin(
            numtaps,
            [low, high],
            pass_zero = (filter_type == 'notch'),
            fs=fs,
            window=win
        )
        w, h = freqz(b, worN=1024, fs=fs)

        # Create the plot
        canvas = self.view.bandpassCanvas if filter_type == 'bandpass' else self.view.notchCanvas
        canvas.ax.clear()
        canvas.ax.plot(w, 20 * np.log10(np.maximum(abs(h), 1e-6)), color="#ab47bc", linewidth=2.0)
        canvas.ax.set_title(f"{filter_type} Filter", fontsize=10, color="#000000")
        canvas.ax.set_ylabel("Gain (dB)", fontsize=9, color="#000000")
        canvas.ax.set_xlim([0, fs / 2])
        canvas.ax.grid(False)
        canvas.ax.tick_params(labelsize=8, colors="#000000")
        canvas.fig.tight_layout()
        canvas.draw()

    def toggle_bands_segmentation(self):
        """
            Function to display the data related to frequency bands when the corresponding checkbox is checked to
            indicate that band segmentation should be performed. If the checkbox is unchecked, the data is hidden.
        """
        visible = self.view.bandCBox.isChecked()
        for widget in [self.view.selectedbandsLabel, self.view.selectedbandsauxLabel, self.view.bandLabel, self.view.bandButton]:
            widget.setVisible(visible)
        self.view.bandLabel.setText("None")
        self.view.band_editor = None
        self.view.band_config_changed.emit()

    def open_band_editor(self, band_type):
        """
            Opens the band editor
        """
        # If it is not initialized, do it
        if self.view.band_editor is None:
            self.view.band_editor = BandTable(
                preprocessing_widget=self,
                band_type=band_type,
                min_broad=self.view.minbroadBox.value(),
                max_broad=self.view.maxbroadBox.value()
            )
            self.view.band_editor.setModal(True)  # Disables the MainWindow without closing or breaking inheritance.
            self.view.band_editor.show()
        self.view.band_editor.show()

    def update_band_label(self, band_type, bands):
        """
            Updates the labels with the names of the selected bands
        """
        self.view.selected_bands_by_type = getattr(self, "selected_bands_by_type", {})
        self.view.selected_bands_by_type[band_type] = bands

        if bands:
            names = [f"{b['name']} ({b['min']}–{b['max']} Hz)" for b in bands]
            self.view.bandLabel.setText(", ".join(names))
        else:
            self.view.bandLabel.setText("None")

        self.view.band_config_changed.emit()

    def get_eeg_params_preprocessing_config(self):
        """
            Function that creates a dictionary with preprocessing configurations.
        """
        config = {
            "fs": self.main_window.sampling_frequency,
            "band_segmentation": True if self.view.bandCBox.isChecked() else None,
            "broadband_min": self.view.minbroadBox.value(),
            "broadband_max": self.view.maxbroadBox.value(),
            "selected_bands": (
                None
                if (not self.view.bandCBox.isChecked() or (
                    len(self.view.selected_bands_by_type.get("segmentation", [])) == 1 and
                    str(self.view.selected_bands_by_type.get("segmentation", [])[0].get("name","")).lower() == "broadband"
                ))
                else self.view.selected_bands_by_type.get("segmentation", [])
            ),
            "selected_files": self.view.selected_files if self.view.selected_files else None,
            "apply_preprocessing": True if self.view.preprocessingButton.isChecked() else None,

            "notch": self.view.notchCBox.isChecked() if self.view.notchCBox else None,
            "notch_min": self.view.minfreqnotchBox.value() if self.view.notchCBox.isChecked() else None,
            "notch_max": self.view.maxfreqnotchBox.value() if self.view.notchCBox.isChecked() else None,
            "notch_order": self.view.orderNotchBox.value() if self.view.notchCBox.isChecked() else None,
            "notch_win": self.view.winnotchBox.currentText() if self.view.notchCBox.isChecked() else None,

            "bandpass": self.view.bpCBox.isChecked() if self.view.bpCBox else None,
            "bp_min": self.view.minfreqbpBox.value() if self.view.bpCBox.isChecked() else None,
            "bp_max": self.view.maxfreqbpBox.value() if self.view.bpCBox.isChecked() else None,
            "bp_order": self.view.orderbpBox.value() if self.view.bpCBox.isChecked() else None,
            "bp_win": self.view.winbpBox.currentText() if self.view.bpCBox.isChecked() else None,

            "car": self.view.carCBox.isChecked() if self.view.carCBox else None,
        }
        return config
