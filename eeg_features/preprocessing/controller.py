import numpy as np
from PySide6 import QtWidgets
from scipy.signal import firwin, freqz
from eeg_features.bands_table import BandTableWidget
from eeg_features.preprocessing.flow import reset_all_controls
import json

class PreprocessingController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self
        self.first_show = False

        # Load config
        self.view.loadButton.clicked.connect(self.load_config)

        # Data preprocessing
        self.view.preprocessingButton.toggled.connect(self.on_preprocessing_toggle)
        # Broadband
        self.view.minbroadBox.valueChanged.connect(self.disable_band_segmentation)
        self.view.maxbroadBox.valueChanged.connect(self.disable_band_segmentation)
        self.view.broadbandButton.clicked.connect(self.broadband_info)
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


    def broadband_info(self):

        QtWidgets.QMessageBox.information(self.view, "Broadband info",
                                      f"We need to know the frequency range of your data in case it has been previously filtered."
                                      f" Otherwise, it will automatically be updated based on the preprocessing selections you made.")


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
        # Reset the RP
        self.view.main_window.stackedWidget.widget(4).rpCBox.setChecked(False)


    def open_band_editor(self):
        """
        Opens the band editor
        """
        # If it is not initialized, do it
        if self.band_editor is None:
            self.band_editor = BandTableWidget(
                preprocessing_widget=self,
                band_type='segmentation'
            )
            self.band_editor.setModal(True)  # Disables the MainWindow without closing or breaking inheritance.
            self.band_editor.show()
        self.band_editor.show()


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

        # Edit the label with the names and ranges of the selected bands, or "None" if no band is selected
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
        # canvas.fig.tight_layout()
        canvas.draw()

    def load_config(self):
        file, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.view, "Select config file", "", "Config file (settings.json)"
        )

        if not file:
            return

        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if data['experiment_type'] != 'eeg_features':
            QtWidgets.QMessageBox.warning(self.view, "Error", "The selected file is not a valid configuration file for this experiment.")
            return

        # PREPROCESSING
        prep_cfg = data["preprocessing"]
        self.view.bandCBox.setChecked(prep_cfg['band_segmentation'] if prep_cfg['band_segmentation'] is not None else False)
        self.view.minbroadBox.setValue(prep_cfg['broadband_min'])
        self.view.maxbroadBox.setValue(prep_cfg['broadband_max'])
        self.update_band_label('segmentation', prep_cfg["selected_bands"])
        self.view.preprocessingButton.setChecked(prep_cfg["apply_preprocessing"] if prep_cfg['apply_preprocessing'] is not None else False)
        self.view.notchCBox.setChecked(prep_cfg['notch'] if prep_cfg['notch'] is not None else False)
        self.view.minfreqnotchBox.setValue(prep_cfg['notch_min'] if prep_cfg['notch_min'] is not None else self.view.defaults["minfreqnotch"])
        self.view.maxfreqnotchBox.setValue(prep_cfg['notch_max'] if prep_cfg['notch_max'] is not None else self.view.defaults["minfreqnotch"])
        self.view.orderNotchBox.setValue(prep_cfg['notch_order'] if prep_cfg['notch_order'] is not None else self.view.defaults["ordernotch"])
        self.view.winnotchBox.setCurrentText(prep_cfg['notch_win'])
        self.view.bpCBox.setChecked(prep_cfg['bandpass'] if prep_cfg['bandpass'] is not None else False)
        self.view.minfreqbpBox.setValue(prep_cfg['bp_min'] if prep_cfg['bp_min'] is not None else self.view.defaults["minfreqbp"])
        self.view.maxfreqbpBox.setValue(prep_cfg['bp_max'] if prep_cfg['bp_max'] is not None else self.view.defaults["maxfreqbp"])
        self.view.orderbpBox.setValue(prep_cfg['bp_order'] if prep_cfg['bp_order'] is not None else self.view.defaults["orderbp"])
        self.view.winbpBox.setCurrentText(prep_cfg['bp_win'])
        self.view.carCBox.setChecked(prep_cfg['car'] if prep_cfg['car'] is not None else False)

        # SEGMENTATION
        segm_cfg = data["segmentation"]
        segm_widget = self.view.main_window.stackedWidget.widget(3)  # widget(3) is the segmentation widget
        segm_widget.conditionRButton.setChecked(segm_cfg['segmentation_type'] == 'condition') # RButton, so it is exclusive with eventRButton
        segm_widget.trialBox.setValue(segm_cfg['trial_length'] if segm_cfg['trial_length'] is not None else segm_widget.defaults['triallength'])
        segm_widget.trialstrideBox.setValue(segm_cfg['trial_stride'] if segm_cfg['trial_stride'] is not None else segm_widget.defaults['trialstride'])
        segm_widget.winBox_1.setValue(segm_cfg['window_start'] if segm_cfg['window_start'] is not None else segm_widget.defaults['windowbox1'])
        segm_widget.winBox_2.setValue(segm_cfg['window_end'] if segm_cfg['window_end'] is not None else segm_widget.defaults['windowbox2'])
        segm_widget.normCBox.setChecked(segm_cfg['norm'] if segm_cfg['norm'] is not None else False)
        if segm_cfg['norm_type'] == 'z':
            segm_widget.zscoreRButton.setChecked(True) # RButton, so it is exclusive with dcRButton
        segm_widget.baselineCBox_1.setValue(segm_cfg['baseline_start'] if segm_cfg['baseline_start'] is not None else segm_widget.defaults['baselinewin1'])
        segm_widget.baselineCBox_2.setValue(segm_cfg['baseline_end'] if segm_cfg['baseline_end'] is not None else segm_widget.defaults['baselinewin2'])
        segm_widget.averageCBox.setChecked(segm_cfg['average'] if segm_cfg['average'] is not None else False)
        segm_widget.thresCBox.setChecked(segm_cfg['thresholding'] if segm_cfg['thresholding'] is not None else False)
        segm_widget.threskBox.setValue(segm_cfg['thres_k'] if segm_cfg['thres_k'] is not None else segm_widget.defaults['threshold'])
        segm_widget.thressampBox.setValue(segm_cfg['thres_samples'] if segm_cfg['thres_samples'] is not None else segm_widget.defaults['thressamples'])
        segm_widget.threschanBox.setValue(segm_cfg['thres_channels'] if segm_cfg['thres_channels'] is not None else segm_widget.defaults['threschannels'])
        segm_widget.resampleCBox.setChecked(segm_cfg['resample'] if segm_cfg['resample'] is not None else False)
        segm_widget.resamplefsBox.setValue(segm_cfg['resample_fs'] if segm_cfg['resample_fs'] is not None else segm_widget.defaults['resamplefs'])

        # PARAMETERS
        params_cfg = data["parameters"]
        params_widget = self.view.main_window.stackedWidget.widget(4)  # widget(4) is the parameters widget
        params_widget.meanCBox.setChecked(params_cfg['mean'] if params_cfg['mean'] is not None else False)
        params_widget.medianCBox.setChecked(params_cfg['median'] if params_cfg['median'] is not None else False)
        params_widget.varianceCBox.setChecked(params_cfg['variance'] if params_cfg['variance'] is not None else False)
        params_widget.kurtosisCBox.setChecked(params_cfg['kurtosis'] if params_cfg['kurtosis'] is not None else False)
        params_widget.skewnessCBox.setChecked(params_cfg['skewness'] if params_cfg['skewness'] is not None else False)
        params_widget.psdCBox.setChecked(params_cfg['psd'] if params_cfg['psd'] is not None else False)
        params_widget.segmentpsdBox.setValue(params_cfg['psd_segment_pct'] if params_cfg['psd_segment_pct'] is not None else params_widget.defaults['psdsegment'])
        params_widget.overlappsdBox.setValue(params_cfg['psd_overlap_pct'] if params_cfg['psd_overlap_pct'] is not None else params_widget.defaults['psdoverlap'])
        params_widget.psdcomboBox.setCurrentText(params_cfg['psd_window'])
        params_widget.rpCBox.setChecked(params_cfg['relative_power'] if params_cfg['relative_power'] is not None else False)
        self.update_band_label('rp', params_cfg["selected_rp_bands"])
        params_widget.apCBox.setChecked(params_cfg['absolute_power'] if params_cfg['absolute_power'] is not None else False)
        params_widget.mfCBox.setChecked(params_cfg['median_frequency'] if params_cfg['median_frequency'] is not None else False)
        params_widget.seCBox.setChecked(params_cfg['spectral_entropy'] if params_cfg['spectral_entropy'] is not None else False)
        params_widget.ctmCBox.setChecked(params_cfg['ctm'] if params_cfg['ctm'] is not None else False)
        params_widget.ctmrBox.setValue(params_cfg['ctm_r'] if params_cfg['ctm_r'] is not None else params_widget.defaults['ctmradius'])
        params_widget.sampenCBox.setChecked(params_cfg['sample_entropy'] if params_cfg['sample_entropy'] is not None else False)
        params_widget.sampenrBox.setValue(params_cfg['sample_entropy_r'] if params_cfg['sample_entropy_r'] is not None else params_widget.defaults['sampradius'])
        params_widget.sampenmBox.setValue(params_cfg['sample_entropy_m'] if params_cfg['sample_entropy_m'] is not None else params_widget.defaults['sampm'])
        params_widget.msampenCBox.setChecked(params_cfg['multiscale_sample_entropy'] if params_cfg['multiscale_sample_entropy'] is not None else False)
        params_widget.msampenrBox.setValue(params_cfg['multiscale_sample_entropy_r'] if params_cfg['multiscale_sample_entropy_r'] is not None else params_widget.defaults['multisampradius'])
        params_widget.msampenmBox.setValue(params_cfg['multiscale_sample_entropy_m'] if params_cfg['multiscale_sample_entropy_m'] is not None else params_widget.defaults['multisampm'])
        params_widget.msampenscaleBox.setValue(params_cfg['multiscale_sample_entropy_scale'] if params_cfg['multiscale_sample_entropy_scale'] is not None else params_widget.defaults['multisampmaxscale'])
        params_widget.lzcCBox.setChecked(params_cfg['lzc'] if params_cfg['lzc'] is not None else False)
        params_widget.mlzcCBox.setChecked(params_cfg['multiscale_lzc'] if params_cfg['multiscale_lzc'] is not None else False)
        if params_cfg['multiscale_lzc_scales'] is not None and params_cfg['multiscale_lzc_scales'].strip():
            params_widget.mlzcEdit.setText(str(params_cfg['multiscale_lzc_scales']))
        params_widget.iacCBox.setChecked(params_cfg['iac'] if params_cfg['iac'] is not None else False)
        params_widget.iacortButton.setChecked(params_cfg['ort_iac'] if params_cfg['ort_iac'] is not None else False)
        params_widget.aecCBox.setChecked(params_cfg['aec'] if params_cfg['aec'] is not None else False)
        params_widget.aecortButton.setChecked(params_cfg['ort_aec'] if params_cfg['ort_aec'] is not None else False)
        params_widget.pliCBox.setChecked(params_cfg['pli'] if params_cfg['pli'] is not None else False)
        params_widget.plvCBox.setChecked(params_cfg['plv'] if params_cfg['plv'] is not None else False)
        params_widget.wpliCBox.setChecked(params_cfg['wpli'] if params_cfg['wpli'] is not None else False)






