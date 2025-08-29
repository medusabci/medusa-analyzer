from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
from bands_table import BandTable
import ast

# Load UI class
ui_parameters_widget = loadUiType('Parameters/parameters_widget.ui')[0]

class ParametersWidget(QtWidgets.QWidget, ui_parameters_widget):
    """
        Main windget element. Manages all the metrics to compute and their parameters. Includes signal metrics,
        connectivity and graph
    """

    def __init__(self, main_window):
        super().__init__()

        # Setup UI
        self.setupUi(self)

        # Define variables
        self.main_window = main_window
        self.last_params = None
        self.selected_bands_by_type = {"rp": []}
        self.rp_band_editor = None

        # Define the header (description) of the widget
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.topContentWidget.setLayout(layout)
        self.logtextBrowser = QtWidgets.QLabel()
        self.logtextBrowser.setTextFormat(QtCore.Qt.RichText)
        self.logtextBrowser.setWordWrap(True)
        self.logtextBrowser.setStyleSheet("""
            QLabel {
                background-color: transparent;
                background: transparent;
                border: none;
            }
        """)
        self.logtextBrowser.setText("""
            <div style="font-size: 11pt; font-family: Arial; line-height: 1;">
                <p>
                    This is the <b>Signal Parameters Module</b> of <i>MEDUSA Analyzer</i>. In this section, you can 
                    configure a wide range of <b>features and metrics</b> to extract from your EEG or biosignal 
                    recordings, including statistical descriptors, spectral features, non-lineal parameters and 
                    connectivity metrics.
                </p>
                <p>
                    Use the checkboxes to enable the metrics of interest. Some metrics require specific 
                    band selections or additional parameters, which can be adjusted after activation.
                </p>
            </div>
        """)
        # Remove background
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Base, palette.color(QtGui.QPalette.Window)) # For this element, Base color will be Window color
        self.topContentWidget.setPalette(palette)
        layout.addWidget(self.logtextBrowser)

        # --- ELEMENT SETUP ---

        # RP AP MF SE - Element setup
        for widget in [self.rpselectedbandsLabel, self.apselectedbandsLabel, self.mfselectedbandsLabel,
                       self.seselectedbandsLabel, self.rpselectedbandsauxLabel, self.mfLabel, self.seLabel,
                       self.rpLabel, self.apLabel, self.rpButton]:
            widget.setVisible(False)
        self.rpCBox.toggled.connect(self.toggle_relative_power)
        self.rpButton.clicked.connect(lambda: self.open_band_table("rp"))

        # STATISTICS AND NONLINEAR - Element setup
        for widget in [self.ctmrLabel, self.ctmrBox, self.sampenmLabel, self.sampenmBox, self.sampenrLabel, self.sampenrBox,
                       self.maxscaleLabel, self.msampenscaleBox, self.msampenmLabel, self.msampenmBox, self.msampenrLabel,
                       self.msampenrBox, self.mlzcscalesLabel, self.mlzcEdit, self.windowpsdLabel,
                       self.psdcomboBox, self.overlappsdBox, self.segmentpsdBox, self.segmentpsdLabel, self.overlappsdLabel]:
            widget.setVisible(False)
        self.msampenCBox.toggled.connect(self.toggle_msampen)
        self.sampenCBox.toggled.connect(self.toggle_sampen)
        self.ctmCBox.toggled.connect(self.toggle_ctm)
        self.psdCBox.toggled.connect(self.toggle_psd)
        self.mlzcCBox.toggled.connect(self.toggle_mlzc)

        # CONNECTIVITY - Element setup
        for widget in [self.iacortLabel, self.iacortButton, self.aecortLabel, self.aecortButton]:
            widget.setVisible(False)
        self.aecCBox.toggled.connect(self.toggle_aec)
        self.iacCBox.toggled.connect(self.toggle_iac)

        # DEFAULT VALUES
        self.defaults = {
            "psdsegment": self.segmentpsdBox.value(),
            "psdoverlap": self.overlappsdBox.value(),
            "ctmradius": self.ctmrBox.value(),
            "sampm": self.sampenmBox.value(),
            "sampradius": self.sampenrBox.value(),
            "multisampmaxscale": self.msampenscaleBox.value(),
            "multisampm": self.msampenmBox.value(),
            "multisampradius": self.msampenrBox.value(),
        }

    # %% --------------------------------------------- SIGNAL METRICS  ------------------------------------------- #
    # RP AP MF SE
    def toggle_psd(self):
        """
            Manages the visibility of the PSD config parameters
        """
        visible = self.psdCBox.isChecked()
        for widget in [self.segmentpsdLabel, self.segmentpsdBox, self.overlappsdLabel, self.overlappsdBox,
                       self.psdcomboBox, self.windowpsdLabel]:
            widget.setVisible(visible)
        self.segmentpsdBox.setValue(self.defaults["psdsegment"])
        self.overlappsdBox.setValue(self.defaults["psdoverlap"])
        self.psdcomboBox.setCurrentIndex(6)

    def toggle_relative_power(self):
        """
            Manages the visibility of the RP config parameters
        """
        visible = self.rpCBox.isChecked()

        if not self.main_window.preproc_config['band_segmentation']:
            self.rpButton.setVisible(visible)
            self.rpselectedbandsLabel.setVisible(visible)
            self.rpselectedbandsauxLabel.setVisible(visible)
            self.rpLabel.setVisible(visible)
            if visible:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Relative Power",
                    "We are currently working only with the broadband signal, since no band filtering "
                    "has been applied during preprocessing.\n\n"
                    "Please use the 'Edit bands' button to define at least one additional frequency band "
                    "in order to enable the calculation of relative power for that band."
                )

        if not visible:
            self.rpLabel.setText("None")
            self.rp_band_editor = None
            self.selected_bands_by_type["rp"] = []
        else:
            broadband = {
                "name": "broadband",
                "min": self.main_window.preproc_config["broadband_min"],
                "max": self.main_window.preproc_config["broadband_max"],
            }
            self.selected_bands_by_type["rp"] = [broadband]
            self.rpLabel.setText(f"broadband ({broadband['min']}–{broadband['max']} Hz)")

    def reset_relative_power(self):
        self.rpCBox.setChecked(False)


    def toggle_ctm(self):
        """
            Manages the visibility of the CTM config parameters
        """
        visible = self.ctmCBox.isChecked()
        for widget in [self.ctmrLabel, self.ctmrBox]:
            widget.setVisible(visible)
        self.ctmrBox.setValue(self.defaults["ctmradius"])

    def toggle_sampen(self):
        """
            Manages the visibility of the SampEn config parameters
        """
        visible = self.sampenCBox.isChecked()
        for widget in [self.sampenmLabel, self.sampenmBox, self.sampenrLabel, self.sampenrBox]:
            widget.setVisible(visible)
        self.sampenmBox.setValue(self.defaults["sampm"])
        self.sampenrBox.setValue(self.defaults["sampradius"])

    def toggle_msampen(self):
        """
            Manages the visibility of the Multiscale SampEn config parameters
        """
        visible = self.msampenCBox.isChecked()
        for widget in [self.maxscaleLabel, self.msampenscaleBox, self.msampenmLabel, self.msampenmBox,
                       self.msampenrLabel, self.msampenrBox]:
            widget.setVisible(visible)
        self.msampenscaleBox.setValue(self.defaults["multisampmaxscale"])
        self.msampenmBox.setValue(self.defaults["multisampm"])
        self.msampenrBox.setValue(self.defaults["multisampradius"])

    def toggle_mlzc(self):
        """
            Manages the visibility of the Multiscale LZC config parameters
        """
        visible = self.mlzcCBox.isChecked()
        for widget in [self.mlzcscalesLabel, self.mlzcEdit]:
            widget.setVisible(visible)
        self.mlzcEdit.setText('[1, 3, 5]')

    def toggle_iac(self):
        """
            Manages the visibility of the IAC config parameters
        """
        visible = self.iacCBox.isChecked()
        if visible: self.iacortButton.setChecked(True)
        else: self.iacortButton.setChecked(False)
        for widget in [self.iacortLabel, self.iacortButton]:
            widget.setVisible(visible)

    def toggle_aec(self):
        """
            Manages the visibility of the AEC config parameters
        """
        visible = self.aecCBox.isChecked()
        if visible: self.aecortButton.setChecked(True)
        else: self.aecortButton.setChecked(False)
        for widget in [self.aecortLabel, self.aecortButton]:
            widget.setVisible(visible)

    def open_band_table(self, band_type):
        """
        Opens the band table dialog for a specific band type (e.g., 'rp', 'ap', etc.)
        """
        if not hasattr(self, "band_table_editors"):
            self.band_table_editors = {}

        if band_type not in self.band_table_editors or self.band_table_editors[band_type] is None:
            previous_bands = self.selected_bands_by_type.get(band_type, [])
            editor = BandTable(
                parameters_widget=self,
                band_type=band_type,
                previous_bands=previous_bands,
                min_broad=self.main_window.min_b,
                max_broad=self.main_window.max_b
            )
            editor.setModal(True)
            editor.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            editor.destroyed.connect(lambda: self._on_band_table_closed(band_type))
            self.band_table_editors[band_type] = editor
            editor.show()

    def update_band_label(self, band_type, bands):
        broadband = {
            "name": "broadband",
            "min": self.main_window.preproc_config["broadband_min"],
            "max": self.main_window.preproc_config["broadband_max"],
        }

        filtered_bands = [b for b in bands if b["name"] != "broadband"]
        self.selected_bands_by_type[band_type] = [broadband] + filtered_bands

        label = getattr(self, f"{band_type}Label", None)
        if label:
            txt = ", ".join(
                [f"{b['name']} ({b['min']}–{b['max']} Hz)" if b['name'] != "broadband" else f"broadband ({b['min']}–{b['max']} Hz)"
                 for b in self.selected_bands_by_type[band_type]]
            )
            label.setText(txt)

    def get_parameters_config(self):
        # Configuration dict
        config = {
            "mean": True if self.meanCBox.isChecked() else None,
            "median": True if self.medianCBox.isChecked() else None,
            "variance": True if self.varianceCBox.isChecked() else None,
            "kurtosis": True if self.kurtosisCBox.isChecked() else None,
            "skewness": True if self.skewnessCBox.isChecked() else None,
            "psd": True if self.psdCBox.isChecked() else None,
            "psd_segment_pct": self.segmentpsdBox.value() if self.psdCBox.isChecked() else None,
            "psd_overlap_pct": self.overlappsdBox.value() if self.psdCBox.isChecked() else None,
            'psd_window': self.psdcomboBox.currentText() if self.psdCBox.isChecked() else None,
            "relative_power": True if self.rpCBox.isChecked() else None,
            "selected_rp_bands": self.selected_bands_by_type["rp"] if self.rpCBox.isChecked() else None,
            "absolute_power": True if self.apCBox.isChecked() else None,
            "median_frequency": True if self.mfCBox.isChecked() else None,
            "spectral_entropy": True if self.seCBox.isChecked() else None,
            "ctm": True if self.ctmCBox.isChecked() else None,
            "ctm_r": self.ctmrBox.value() if self.ctmCBox.isChecked() else None,
            "sample_entropy": True if self.sampenCBox.isChecked() else None,
            "sample_entropy_r": self.sampenrBox.value() if self.sampenCBox.isChecked() else None,
            "sample_entropy_m": self.sampenmBox.value() if self.sampenCBox.isChecked() else None,
            "multiscale_sample_entropy": True if self.msampenCBox.isChecked() else None,
            "multiscale_sample_entropy_r": self.msampenrBox.value() if self.msampenCBox.isChecked() else None,
            "multiscale_sample_entropy_m": self.msampenmBox.value() if self.msampenCBox.isChecked() else None,
            "multiscale_sample_entropy_scale": self.msampenscaleBox.value() if self.msampenCBox.isChecked() else None,
            "lzc": True if self.lzcCBox.isChecked() else None,
            "multiscale_lzc": True if self.mlzcCBox.isChecked() else None,
            "multiscale_lzc_scales": ast.literal_eval(self.mlzcEdit.text()) if self.mlzcCBox.isChecked()
                                                                               and self.mlzcEdit.text().strip() else None,
            "iac": True if self.iacCBox.isChecked() else None,
            "ort_iac": True if self.iacortButton.isChecked() and self.iacCBox.isChecked() else None,
            "aec": True if self.aecCBox.isChecked() else None,
            "ort_aec": True if self.aecortButton.isChecked() and self.aecCBox.isChecked() else None,
            "pli": True if self.pliCBox.isChecked() else None,
            "plv": True if self.plvCBox.isChecked() else None,
            "wpli": True if self.wpliCBox.isChecked() else None
        }
        return config
