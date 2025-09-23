import numpy as np
from PySide6 import QtWidgets
from scipy.signal import firwin, freqz
from ecg_features.preprocessing.flow import reset_all_controls

class PreprocessingController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self
        self.first_show = False

        # Data preprocessing
        self.view.preprocessingButton.toggled.connect(self.on_preprocessing_toggle)

        # Baseline
        self.view.baselineCBox.toggled.connect(self.on_baseline_toggle)
        self.view.baselineCBox.toggled.connect(lambda: self.update_filter_plot('baseline'))
        self.view.drawbaselineButton.clicked.connect(lambda: self.update_filter_plot('baseline'))
        bg_color = self.view.palette().color(self.view.backgroundRole()).name()
        self.view.baselineCanvas.fig.patch.set_facecolor(bg_color)
        self.view.baselineCanvas.ax.set_facecolor(bg_color)
        self.view.cutoffbaselineBox.valueChanged.connect(
            lambda: self.view.minbroadLabel.setText(str(self.view.cutoffbaselineBox.value())))

        # Bandpass
        self.view.bpCBox.toggled.connect(self.on_bandpass_toggle)
        self.view.bpCBox.toggled.connect(lambda: self.update_filter_plot('bandpass'))
        self.view.drawbpButton.clicked.connect(lambda: self.update_filter_plot('bandpass'))
        self.view.bandpassCanvas.fig.patch.set_facecolor(bg_color)
        self.view.bandpassCanvas.ax.set_facecolor(bg_color)
        self.view.minfreqbpBox.editingFinished.connect(lambda: self.validate_filter_bounds("bandpass"))
        self.view.maxfreqbpBox.editingFinished.connect(lambda: self.validate_filter_bounds("bandpass"))
        self.view.minfreqbpBox.valueChanged.connect(lambda: self.view.minbroadLabel.setText(str(self.view.minfreqbpBox.value())))
        self.view.maxfreqbpBox.valueChanged.connect(lambda: self.view.maxbroadLabel.setText(str(self.view.maxfreqbpBox.value())))

        # HRV
        self.view.hrvCBox.toggled.connect(self.on_hrv_toggle)
        self.view.rrcorrectionCBox.toggled.connect(self.on_rrcorrection_toggle)
        self.view.resampleCBox.toggled.connect(self.on_resample_toggle)

        # Set initial state
        self.view.shown.connect(self.on_show_event)

    def on_preprocessing_toggle(self, checked):
        """
        This function shows or hides the preprocessing controls depending on whether the user chooses to apply them
        or not.
        """
        if not checked:
            reset_all_controls(self)
            return
        else: # Show all the checkboxes, but keep their parameters hidden
            elements = [
                self.view.baselineLabel, self.view.baselineCBox, self.view.baselinegroupBox,
                self.view.bpLabel, self.view.bpCBox,  self.view.bpgroupBox,
                self.view.normLabel, self.view.normCBox, self.view.normgroupBox,
            ]
            for elm in elements:
                elm.setVisible(True)

    def on_baseline_toggle(self, checked):
        """
        Shows (or hides) the parameters associated with 'notch_filter' when its main checkbox is checked (or
        unchecked).
        """

        # Show (or hide)
        self.view.baselinePlotWidget.setVisible(checked)
        self.view.cutoffbaselineLabel.setVisible(checked)
        self.view.cutoffbaselineBox.setVisible(checked)
        self.view.orderbaselineLabel.setVisible(checked)
        self.view.orderbaselineBox.setVisible(checked)
        self.view.drawbaselineButton.setVisible(checked)
        self.view.winbaselineBox.setVisible(checked)
        self.view.winbaselineLabel.setVisible(checked)
        self.view.minbroadLabel.setText(str(self.view.cutoffbaselineBox.value()))

        # Reset default values
        if not checked:
            self.view.cutoffbaselineBox.setValue(self.view.defaults["cutoffbaseline"])
            self.view.orderbaselineBox.setValue(self.view.defaults["orderbaseline"])
            self.view.winbaselineBox.setCurrentIndex(9) # Hamming

    def on_bandpass_toggle(self, checked):
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
        self.view.minbroadLabel.setText(str(self.view.minfreqbpBox.value()))
        self.view.maxbroadLabel.setText(str(self.view.maxfreqbpBox.value()))

        # Reset default values
        if not checked:
            self.view.minfreqbpBox.setValue(self.view.defaults["minfreqbp"])
            self.view.maxfreqbpBox.setValue(self.view.defaults["maxfreqbp"])
            self.view.orderbpBox.setValue(self.view.defaults["orderbp"])
            self.view.winbpBox.setCurrentIndex(9) # Hamming
            self.view.minbroadLabel.setText("0")
            self.view.maxbroadLabel.setText(str(self.view.main_window.stackedWidget.widget(1).controller.biosignal_info['fs']/2))

    def validate_filter_bounds(self, filter_type):
        """Validate filter bounds and compatibility between broadband, bandpass, and baseline filters."""
        # Get values and defaults
        if filter_type == "bandpass":
            min_val, max_val = self.view.minfreqbpBox.value(), self.view.maxfreqbpBox.value()
            if max_val <= min_val:
                QtWidgets.QMessageBox.warning(self.view, f"Invalid {filter_type}",
                                              f"Max {max_val} must be greater than Min {min_val}.")
                getattr(self.view, f"minfreqbpBox").setValue(self.view.defaults["minfreqbp"])
                getattr(self.view, f"maxfreqbpBox").setValue(self.view.defaults["maxfreqbp"])
                return False

        elif filter_type == "baseline":
            cutoff = self.view.cutoffbaselineBox.value()

            min_bp = self.view.minfreqbpBox.value()
            if self.view.bpCBox.isChecked() and cutoff > self.view.minfreqbpBox.value():
                QtWidgets.QMessageBox.warning(
                    self.view,
                    "Incompatible filters",
                    f"Baseline cutoff ({cutoff} Hz) should be lower than bandpass minimum ({min_bp} Hz)."
                )
                self.view.cutoffbaselineBox.setValue(self.view.defaults["cutoffbaseline"])
                return False
        return True

    def validate_interval_bounds(self):
        """Validate interval bounds and compatibility. """
        # Get values and defaults
        min_val, max_val = self.view.minrrBox.value(), self.view.maxrrBox.value()
        if max_val <= min_val:
            QtWidgets.QMessageBox.warning(self.view, f"Invalid RR interval correction",
                                          f"Max {max_val} must be greater than Min {min_val}.")
            getattr(self.view, f"minrrBox").setValue(self.view.defaults["minrrtime"])
            getattr(self.view, f"maxrrBox").setValue(self.view.defaults["maxrrtime"])
            return False

    def on_hrv_toggle(self, checked):
        """
        This function shows or hides the hrv controls depending on whether the user chooses to apply them
        or not.
        """
        if not checked:
            # Hide everything when HRV disabled
            elements = [
                self.view.hrvinterpolLabel, self.view.hrvinterpolBox,
                self.view.rrcorrectionLabel, self.view.rrcorrectionCBox,
                self.view.resampleLabel, self.view.resampleCBox,
            ]
            for elm in elements:
                elm.setVisible(False)

            # Force-hide parameter groups
            self.on_rrcorrection_toggle(False)
            self.on_resample_toggle(False)
            return

            # If HRV enabled: show interpolation and the checkboxes (unchecked)
        self.view.hrvinterpolLabel.setVisible(True)
        self.view.hrvinterpolBox.setVisible(True)

        # Show RR correction label + checkbox
        self.view.rrcorrectionLabel.setVisible(True)
        self.view.rrcorrectionCBox.setVisible(True)
        self.view.rrcorrectionCBox.setChecked(False)

        # Show Resample label + checkbox
        self.view.resampleLabel.setVisible(True)
        self.view.resampleCBox.setVisible(True)
        self.view.resampleCBox.setChecked(False)

    def on_rrcorrection_toggle(self, checked):
        """
        Show or hide correction controls based on the checkbox state. Resets resample frequency spinbox when disabled.
        """
        rr_elements = [
            self.view.minrrLabel, self.view.minrrBox,
            self.view.maxrrLabel, self.view.maxrrBox,
            self.view.rrmethodLabel, self.view.rrmethodBox,
        ]

        for w in rr_elements:
            w.setVisible(checked)

        # Toggle label depending on HRV
        self.view.rrcorrectionLabel.setVisible(self.view.hrvCBox.isChecked() and not checked)

        if not checked:
            # Reset defaults
            self.view.minrrBox.setValue(self.view.defaults["minrrtime"])
            self.view.maxrrBox.setValue(self.view.defaults["maxrrtime"])
            self.view.rrmethodBox.setCurrentIndex(2)  # Interpolate


    def on_resample_toggle(self, checked):
        """
        Show or hide resampling controls based on the checkbox state. Resets resample frequency spinbox when disabled.
        """
        resample_elements = [self.view.newfsLabel, self.view.resamplefsBox, self.view.resampleLabelNyquist]

        for w in resample_elements:
            w.setVisible(checked)

        # Toggle label depending on HRV
        self.view.resampleLabel.setVisible(self.view.hrvCBox.isChecked() and not checked)

        if checked:
            self.view.resampleLabelNyquist.setText("Recommended fs: 4 Hz")
        else:
            # Reset defaults
            self.view.resamplefsBox.setValue(self.view.defaults["resamplefs"])

    def on_show_event(self):
        if not self.first_show:
            self.first_show = True
            files_widget_controller = self.view.main_window.stackedWidget.widget(1).controller # widget(1) is the file selection widget
            fs = files_widget_controller.biosignal_info['fs']
            nyquist = fs / 2
            # Limit max values of the spinboxes to fs/2
            spinboxes = [
                self.view.cutoffbaselineBox,
                self.view.minfreqbpBox, self.view.maxfreqbpBox,
            ]
            for sb in spinboxes:
                sb.setMaximum(nyquist)

            # Set default values for broadband
            self.view.minbroadLabel.setText("0")
            self.view.maxbroadLabel.setText(str(nyquist))

    def update_filter_plot(self, filter_type):
        """
        Function that plots a filter response.
        Supports:
            - 'bandpass' (low and high cutoff frequencies)
            - 'baseline' (high-pass filter with single cutoff frequency)
        """
        if filter_type == 'bandpass':
            # Bandpass parameters
            low = self.view.minfreqbpBox.value()
            high = self.view.maxfreqbpBox.value() - 1e-6  # So that high = fs/2 is allowed
            numtaps = self.view.orderbpBox.value()
            win = self.view.winbpBox.currentText()

            # Filter design
            cutoff = [low, high]
            pass_zero = False  # bandpass

        elif filter_type == 'baseline':
            # Baseline = high-pass filter
            low = self.view.cutoffbaselineBox.value()
            numtaps = self.view.orderbaselineBox.value()
            win = self.view.winbaselineBox.currentText()

            # Filter design
            cutoff = low
            pass_zero = False  # high-pass

            # Ensure odd number of taps (required for high-pass FIR)
            if numtaps % 2 == 0:
                numtaps += 1
                self.view.orderbaselineBox.setValue(numtaps)

        else:
            return  # unsupported type

        # Validate cutoff bounds
        if not self.validate_filter_bounds(filter_type):
            return

        # Sampling frequency from loaded biosignal
        fs = self.view.main_window.stackedWidget.widget(1).controller.biosignal_info['fs'] # widget (1) is the selected files widget

        # FIR filter design
        b = firwin(
            numtaps,
            cutoff,
            pass_zero=pass_zero,
            fs=fs,
            window=win
        )
        w, h = freqz(b, worN=1024, fs=fs)

        # Select canvas
        if filter_type == 'bandpass':
            canvas = self.view.bandpassCanvas
        else:  # baseline
            canvas = self.view.baselineCanvas

        # Plot response
        canvas.ax.clear()
        canvas.ax.plot(w, 20 * np.log10(np.maximum(abs(h), 1e-6)), color="#ab47bc", linewidth=2.0)
        canvas.ax.set_title(f"{filter_type.capitalize()} Filter", fontsize=10, color="#000000")
        canvas.ax.set_ylabel("Gain (dB)", fontsize=9, color="#000000")
        canvas.ax.set_xlim([0, fs / 2])
        canvas.ax.grid(False)
        canvas.ax.tick_params(labelsize=8, colors="#000000")
        # canvas.fig.tight_layout()
        canvas.draw()