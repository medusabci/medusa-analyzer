from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
from eeg_features.bands_table import BandTable
import ast

class ParametersController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self

        # Relative power
        self.view.rpCBox.toggled.connect(self.toggle_relative_power)
        self.view.rpButton.clicked.connect(lambda: self.open_band_table("rp"))

        # STATISTICS AND NONLINEAR - Element setup
        self.view.msampenCBox.toggled.connect(self.toggle_msampen)
        self.view.sampenCBox.toggled.connect(self.toggle_sampen)
        self.view.ctmCBox.toggled.connect(self.toggle_ctm)
        self.view.psdCBox.toggled.connect(self.toggle_psd)
        self.view.mlzcCBox.toggled.connect(self.toggle_mlzc)

        # CONNECTIVITY - Element setup
        self.view.aecCBox.toggled.connect(self.toggle_aec)
        self.view.iacCBox.toggled.connect(self.toggle_iac)

    # RP AP MF SE
    def toggle_psd(self):
        """
            Manages the visibility of the PSD config parameters
        """
        visible = self.view.psdCBox.isChecked()
        for widget in [self.view.segmentpsdLabel, self.view.segmentpsdBox, self.view.overlappsdLabel, self.view.overlappsdBox,
                       self.view.psdcomboBox, self.view.windowpsdLabel]:
            widget.setVisible(visible)
        self.view.segmentpsdBox.setValue(self.view.defaults["psdsegment"])
        self.view.overlappsdBox.setValue(self.view.defaults["psdoverlap"])
        self.view.psdcomboBox.setCurrentIndex(6)

    def toggle_relative_power(self):
        """
            Manages the visibility of the RP config parameters
        """
        visible = self.view.rpCBox.isChecked()

        if not self.view.main_window.preproc_config['band_segmentation']:
            self.view.rpButton.setVisible(visible)
            self.view.rpselectedbandsLabel.setVisible(visible)
            self.view.rpselectedbandsauxLabel.setVisible(visible)
            self.view.rpLabel.setVisible(visible)
            if visible:
                QtWidgets.QMessageBox.warning(
                    self.view,
                    "Relative Power",
                    "We are currently working only with the broadband signal, since no band filtering "
                    "has been applied during preprocessing.\n\n"
                    "Please use the 'Edit bands' button to define at least one additional frequency band "
                    "in order to enable the calculation of relative power for that band."
                )

        if not visible:
            self.view.rpLabel.setText("None")
            self.view.rp_band_editor = None
            self.view.selected_bands_by_type["rp"] = []
        else:
            broadband = {
                "name": "broadband",
                "min": self.view.main_window.preproc_config["broadband_min"],
                "max": self.view.main_window.preproc_config["broadband_max"],
            }
            self.view.selected_bands_by_type["rp"] = [broadband]
            self.view.rpLabel.setText(f"broadband ({broadband['min']}–{broadband['max']} Hz)")

    def reset_relative_power(self):
        self.view.rpCBox.setChecked(False)

    def toggle_ctm(self):
        """
            Manages the visibility of the CTM config parameters
        """
        visible = self.view.ctmCBox.isChecked()
        for widget in [self.view.ctmrLabel, self.view.ctmrBox]:
            widget.setVisible(visible)
        self.view.ctmrBox.setValue(self.view.defaults["ctmradius"])

    def toggle_sampen(self):
        """
            Manages the visibility of the SampEn config parameters
        """
        visible = self.view.sampenCBox.isChecked()
        for widget in [self.view.sampenmLabel, self.view.sampenmBox, self.view.sampenrLabel, self.view.sampenrBox]:
            widget.setVisible(visible)
        self.view.sampenmBox.setValue(self.view.defaults["sampm"])
        self.view.sampenrBox.setValue(self.view.defaults["sampradius"])

    def toggle_msampen(self):
        """
            Manages the visibility of the Multiscale SampEn config parameters
        """
        visible = self.view.msampenCBox.isChecked()
        for widget in [self.view.maxscaleLabel, self.view.msampenscaleBox, self.view.msampenmLabel, self.view.msampenmBox,
                       self.view.msampenrLabel, self.view.msampenrBox]:
            widget.setVisible(visible)
        self.view.msampenscaleBox.setValue(self.view.defaults["multisampmaxscale"])
        self.view.msampenmBox.setValue(self.view.defaults["multisampm"])
        self.view.msampenrBox.setValue(self.view.defaults["multisampradius"])

    def toggle_mlzc(self):
        """
            Manages the visibility of the Multiscale LZC config parameters
        """
        visible = self.view.mlzcCBox.isChecked()
        for widget in [self.view.mlzcscalesLabel, self.view.mlzcEdit]:
            widget.setVisible(visible)
        self.view.mlzcEdit.setText('[1, 3, 5]')

    def toggle_iac(self):
        """
            Manages the visibility of the IAC config parameters
        """
        visible = self.view.iacCBox.isChecked()
        if visible:
            self.view.iacortButton.setChecked(True)
        else:
            self.view.iacortButton.setChecked(False)
        for widget in [self.view.iacortLabel, self.view.iacortButton]:
            widget.setVisible(visible)

    def toggle_aec(self):
        """
            Manages the visibility of the AEC config parameters
        """
        visible = self.view.aecCBox.isChecked()
        if visible:
            self.view.aecortButton.setChecked(True)
        else:
            self.view.aecortButton.setChecked(False)
        for widget in [self.view.aecortLabel, self.view.aecortButton]:
            widget.setVisible(visible)

    def open_band_table(self, band_type):
        """
        Opens the band table dialog for a specific band type (e.g., 'rp', 'ap', etc.)
        """
        if not hasattr(self, "band_table_editors"):
            self.band_table_editors = {}

        if band_type not in self.band_table_editors or self.band_table_editors[band_type] is None:
            previous_bands = self.view.selected_bands_by_type.get(band_type, [])
            editor = BandTable(
                parameters_widget=self,
                band_type=band_type,
                previous_bands=previous_bands,
                min_broad=self.view.main_window.min_b,
                max_broad=self.view.main_window.max_b
            )
            editor.setModal(True)
            editor.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            editor.destroyed.connect(lambda: self._on_band_table_closed(band_type))
            self.band_table_editors[band_type] = editor
            editor.show()

    def update_band_label(self, band_type, bands):
        broadband = {
            "name": "broadband",
            "min": self.view.main_window.preproc_config["broadband_min"],
            "max": self.view.main_window.preproc_config["broadband_max"],
        }

        filtered_bands = [b for b in bands if b["name"] != "broadband"]
        self.view.selected_bands_by_type[band_type] = [broadband] + filtered_bands

        label = getattr(self, f"{band_type}Label", None)
        if label:
            txt = ", ".join(
                [f"{b['name']} ({b['min']}–{b['max']} Hz)" if b[
                                                                  'name'] != "broadband" else f"broadband ({b['min']}–{b['max']} Hz)"
                 for b in self.view.selected_bands_by_type[band_type]]
            )
            label.setText(txt)

    def get_parameters_config(self):
        # Configuration dict
        config = {
            "mean": True if self.view.meanCBox.isChecked() else None,
            "median": True if self.view.medianCBox.isChecked() else None,
            "variance": True if self.view.varianceCBox.isChecked() else None,
            "kurtosis": True if self.view.kurtosisCBox.isChecked() else None,
            "skewness": True if self.view.skewnessCBox.isChecked() else None,
            "psd": True if self.view.psdCBox.isChecked() else None,
            "psd_segment_pct": self.view.segmentpsdBox.value() if self.view.psdCBox.isChecked() else None,
            "psd_overlap_pct": self.view.overlappsdBox.value() if self.view.psdCBox.isChecked() else None,
            'psd_window': self.view.psdcomboBox.currentText() if self.view.psdCBox.isChecked() else None,
            "relative_power": True if self.view.rpCBox.isChecked() else None,
            "selected_rp_bands": self.view.selected_bands_by_type["rp"] if self.view.rpCBox.isChecked() else None,
            "absolute_power": True if self.view.apCBox.isChecked() else None,
            "median_frequency": True if self.view.mfCBox.isChecked() else None,
            "spectral_entropy": True if self.view.seCBox.isChecked() else None,
            "ctm": True if self.view.ctmCBox.isChecked() else None,
            "ctm_r": self.view.ctmrBox.value() if self.view.ctmCBox.isChecked() else None,
            "sample_entropy": True if self.view.sampenCBox.isChecked() else None,
            "sample_entropy_r": self.view.sampenrBox.value() if self.view.sampenCBox.isChecked() else None,
            "sample_entropy_m": self.view.sampenmBox.value() if self.view.sampenCBox.isChecked() else None,
            "multiscale_sample_entropy": True if self.view.msampenCBox.isChecked() else None,
            "multiscale_sample_entropy_r": self.view.msampenrBox.value() if self.view.msampenCBox.isChecked() else None,
            "multiscale_sample_entropy_m": self.view.msampenmBox.value() if self.view.msampenCBox.isChecked() else None,
            "multiscale_sample_entropy_scale": self.view.msampenscaleBox.value() if self.view.msampenCBox.isChecked() else None,
            "lzc": True if self.view.lzcCBox.isChecked() else None,
            "multiscale_lzc": True if self.view.mlzcCBox.isChecked() else None,
            "multiscale_lzc_scales": ast.literal_eval(self.view.mlzcEdit.text()) if self.view.mlzcCBox.isChecked()
                                                                               and self.view.mlzcEdit.text().strip() else None,
            "iac": True if self.view.iacCBox.isChecked() else None,
            "ort_iac": True if self.view.iacortButton.isChecked() and self.view.iacCBox.isChecked() else None,
            "aec": True if self.view.aecCBox.isChecked() else None,
            "ort_aec": True if self.view.aecortButton.isChecked() and self.view.aecCBox.isChecked() else None,
            "pli": True if self.view.pliCBox.isChecked() else None,
            "plv": True if self.view.plvCBox.isChecked() else None,
            "wpli": True if self.view.wpliCBox.isChecked() else None
        }
        return config
