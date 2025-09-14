import numpy as np
from PySide6 import QtWidgets
from scipy.signal import firwin, freqz
from eeg_features.bands_table import BandTableWidget
from eeg_features.preprocessing.flow import reset_all_controls

class PreprocessingController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self
        self.first_show = False

        # Data preprocessing
        self.view.preprocessingButton.toggled.connect(self.on_preprocessing_toggle)
        # Broadband
        self.view.minbroadBox.valueChanged.connect(self.disable_band_segmentation)
        self.view.maxbroadBox.valueChanged.connect(self.disable_band_segmentation)
        # Notch
        self.view.notchCBox.toggled.connect(self.on_notch_toggle)
        self.view.notchCBox.toggled.connect(lambda: self.update_filter_plot('notch'))
        self.view.drawnotchButton.clicked.connect(lambda: self.update_filter_plot('notch'))
        bg_color = self.view.palette().color(self.view.backgroundRole()).name()
        self.view.notchCanvas.fig.patch.set_facecolor(bg_color)
        self.view.notchCanvas.ax.set_facecolor(bg_color)
        self.view.minfreqnotchBox.editingFinished.connect(lambda: self.validate_filter_bounds("notch"))
        self.view.maxfreqnotchBox.editingFinished.connect(lambda: self.validate_filter_bounds("notch"))
        # Bandpass
        self.view.bpCBox.toggled.connect(self.on_bandpass_toggle)
        self.view.bpCBox.toggled.connect(lambda: self.update_filter_plot('bandpass'))
        self.view.drawbpButton.clicked.connect(lambda: self.update_filter_plot('bandpass'))
        self.view.bandpassCanvas.fig.patch.set_facecolor(bg_color)
        self.view.bandpassCanvas.ax.set_facecolor(bg_color)
        self.view.minfreqbpBox.editingFinished.connect(lambda: self.validate_filter_bounds("bandpass"))
        self.view.maxfreqbpBox.editingFinished.connect(lambda: self.validate_filter_bounds("bandpass"))
        self.view.minfreqbpBox.valueChanged.connect(lambda: self.view.minbroadBox.setValue(self.view.minfreqbpBox.value()))
        self.view.maxfreqbpBox.valueChanged.connect(lambda: self.view.maxbroadBox.setValue(self.view.maxfreqbpBox.value()))
        self.view.minfreqbpBox.valueChanged.connect(self.disable_band_segmentation)
        self.view.maxfreqbpBox.valueChanged.connect(self.disable_band_segmentation)

        # Band segmentation
        self.view.bandCBox.toggled.connect(self.on_band_filtering_toggle)
        self.view.bandButton.clicked.connect(self.open_band_editor)
        # self.selected_bands = []
        self.band_editor = None

        # Set initial state
        self.view.shown.connect(self.on_show_event)
        reset_all_controls(self)


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
                self.view.cargroupBox, self.view.carLabel, self.view.carCBox,
                self.view.notchfilterLabel, self.view.notchCBox, self.view.notchgroupBox,
                self.view.bpLabel, self.view.bpCBox, self.view.bpgroupBox,
            ]
            for elm in elements:
                elm.setVisible(True)


    def on_notch_toggle(self, checked):
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
            self.view.winnotchBox.setCurrentIndex(9) # Hamming


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
        self.view.maxbroadBox.setValue(self.view.maxfreqbpBox.value())

        # Reset default values
        if not checked:
            self.view.minfreqbpBox.setValue(self.view.defaults["minfreqbp"])
            self.view.maxfreqbpBox.setValue(self.view.defaults["maxfreqbp"])
            self.view.orderbpBox.setValue(self.view.defaults["orderbp"])
            self.view.winbpBox.setCurrentIndex(9) # Hamming
            self.view.maxbroadBox.setValue(self.view.main_window.stackedWidget.widget(1).controller.biosignal_info['fs']/2)

    def validate_filter_bounds(self, filter_type):
        """Validate filter bounds and compatibility between broadband, bandpass, and notch filters."""
        # Get values and defaults
        if filter_type == "bandpass":
            min_val, max_val = self.view.minfreqbpBox.value(), self.view.maxfreqbpBox.value()
            dmin, dmax = "minfreqbp", "maxfreqbp"
        else:  # notch
            min_val, max_val = self.view.minfreqnotchBox.value(), self.view.maxfreqnotchBox.value()
            dmin, dmax = "minfreqnotch", "maxfreqnotch"

        # 1. Own bounds check
        if max_val <= min_val:
            QtWidgets.QMessageBox.warning(self.view, f"Invalid {filter_type}",
                                          f"Max {max_val} must be greater than Min {min_val}.")
            getattr(self.view, f"{dmin}Box").setValue(self.view.defaults[dmin])
            getattr(self.view, f"{dmax}Box").setValue(self.view.defaults[dmax])
            return False

        # 2. Notch inside bandpass. If not, adjust notch values to a sensible window inside the bandpass
        if self.view.bpCBox.isChecked() and self.view.notchCBox.isChecked():
            if not (self.view.minfreqbpBox.value() <= self.view.minfreqnotchBox.value() <= self.view.maxfreqbpBox.value()
                and self.view.minfreqbpBox.value() <= self.view.maxfreqnotchBox.value() <= self.view.maxfreqbpBox.value()):
                bp_min, bp_max = self.view.minfreqbpBox.value(), self.view.maxfreqbpBox.value()
                bp_w = bp_max - bp_min
                default_w = self.view.defaults["maxfreqnotch"] - self.view.defaults["minfreqnotch"]
                # choose notch width: prefer default_w, but limit to a fraction of bandpass and a sensible minimum
                notch_w = min(default_w, max(0.5, bp_w * 0.25))
                if notch_w >= bp_w: notch_w = max(0.5, bp_w * 0.5)
                # center the notch near the default center but clamp it inside bandpass margins
                default_center = (self.view.defaults["minfreqnotch"] + self.view.defaults["maxfreqnotch"]) / 2
                center = min(max(default_center, bp_min + notch_w / 2), bp_max - notch_w / 2)
                new_min, new_max = center - notch_w / 2, center + notch_w / 2
                self.view.minfreqnotchBox.setValue(new_min);
                self.view.maxfreqnotchBox.setValue(new_max)
                QtWidgets.QMessageBox.warning(self.view, "Notch adjusted",
                                              f"Notch was outside bandpass — adjusted to {new_min:.2f}–{new_max:.2f} Hz.")
                return True
        return True


    def on_band_filtering_toggle(self, checked):
        """
        Function to display the data related to frequency bands when the corresponding checkbox is checked to
        indicate that band filtering should be performed. If the checkbox is unchecked, the data is hidden.
        """
        for widget in [self.view.selectedbandsLabel, self.view.selectedbandsauxLabel, self.view.bandLabel, self.view.bandButton]:
            widget.setVisible(checked)
        self.view.bandLabel.setText("None")
        self.band_editor = None


    def open_band_editor(self):
        """
        Opens the band editor
        """
        idx = self.view.main_window.stackedWidget.currentIndex()
        # If it is not initialized, do it
        if self.band_editor is None:
            self.band_editor = BandTableWidget(
                preprocessing_widget=self,
                band_type='segmentation'
            )
            self.band_editor.setModal(True)  # Disables the MainWindow without closing or breaking inheritance.
            self.band_editor.show()
        self.band_editor.show()
        self.view.main_window.stackedWidget.widget(idx+2).rpCBox.setChecked(False)


    def disable_band_segmentation(self):
        """
        Disables band segmentation if the broadband limits are modified so that there is no conflict.
        """
        if self.view.bandCBox.isChecked():
            self.view.bandCBox.setChecked(False)


    def update_band_label(self, filtering_target, bands):
        """
        Updates the labels with the names of the selected bands
        """
        self.view.selected_bands_by_type = getattr(self, "selected_bands_by_type", {})
        self.view.selected_bands_by_type[filtering_target] = bands

        if bands:
            names = [f"{b['name']} ({b['min']}–{b['max']} Hz)" for b in bands]
            self.view.bandLabel.setText(", ".join(names))
        else:
            self.view.bandLabel.setText("None")


    def on_show_event(self):
        if not self.first_show:
            self.first_show = True
            files_widget_controller = self.view.main_window.stackedWidget.widget(1).controller # widget(1) is the file selection widget
            fs = files_widget_controller.biosignal_info['fs']
            nyquist = fs / 2
            # Limit max values of the spinboxes to fs/2
            spinboxes = [
                self.view.minbroadBox, self.view.maxbroadBox,
                self.view.minfreqnotchBox, self.view.maxfreqnotchBox,
                self.view.minfreqbpBox, self.view.maxfreqbpBox,
            ]
            for sb in spinboxes:
                sb.setMaximum(nyquist)

            # Set default values for broadband
            self.view.minbroadBox.setValue(0.5)
            self.view.maxbroadBox.setValue(nyquist)

            if not files_widget_controller.selected_files:
                reset_all_controls(self)

    def update_filter_plot(self, filter_type):
        """
        Function that plots a filter
        """
        if filter_type == 'bandpass':
            low = self.view.minfreqbpBox.value()
            high = self.view.maxfreqbpBox.value() - 1e-6 # So that high = fs/2 is allowed
            numtaps = self.view.orderbpBox.value()
            win = self.view.winbpBox.currentText()

        else:  # notch
            low = self.view.minfreqnotchBox.value()
            high = self.view.maxfreqnotchBox.value()
            numtaps = self.view.orderNotchBox.value()
            win = self.view.winnotchBox.currentText()

            if numtaps % 2 == 0:
                numtaps += 1
                self.view.orderNotchBox.setValue(numtaps)

        if not self.validate_filter_bounds(filter_type):
            return

        fs = self.view.main_window.stackedWidget.widget(1).controller.biosignal_info['fs'] # widget(1) is the file selection widget
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








