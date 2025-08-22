from PyQt5 import QtWidgets, uic, QtCore
from bands_table import BandTable
import ast

class ParametersWidget(QtWidgets.QWidget):
    """
        Main windget element. Manages all the metrics to compute and their parameters. Includes signal metrics,
        connectivity and graph
    """

    def __init__(self, main_window):
        super().__init__()
        uic.loadUi('Parameters/parameters_widget.ui', self)

        # Define variables
        self.main_window = main_window
        self.last_params = None
        self.selected_bands_by_type = {
            "rp": [],
            "ap": [],
            "mf": [],
            "se": []
        }
        self.rp_band_editor = None
        self.ap_band_editor = None
        self.mf_band_editor = None
        self.se_band_editor = None

        # Define the header (description) of the widget
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.topContentWidget = self.findChild(QtWidgets.QWidget, "topContentWidget")
        self.topContentWidget.setLayout(layout)
        self.logtextBrowser = QtWidgets.QLabel()
        self.logtextBrowser.setTextFormat(QtCore.Qt.RichText)
        self.logtextBrowser.setWordWrap(True)
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
        layout.addWidget(self.logtextBrowser)


        #%% --------------------------------------------- SIGNAL METRICS  ------------------------------------------- #
        # RP AP MF SE
        self.rpCBox = self.findChild(QtWidgets.QCheckBox, "rpCBox")
        self.apCBox = self.findChild(QtWidgets.QCheckBox, "apCBox")
        self.mfCBox = self.findChild(QtWidgets.QCheckBox, "mfCBox")
        self.seCBox = self.findChild(QtWidgets.QCheckBox, "seCBox")
        self.rpselectedbandsLabel = self.findChild(QtWidgets.QLabel, "rpselectedbandsLabel")
        self.apselectedbandsLabel = self.findChild(QtWidgets.QLabel, "apselectedbandsLabel")
        self.mfselectedbandsLabel = self.findChild(QtWidgets.QLabel, "mfselectedbandsLabel")
        self.seselectedbandsLabel = self.findChild(QtWidgets.QLabel, "seselectedbandsLabel")
        self.rpselectedbandsauxLabel = self.findChild(QtWidgets.QLabel, "rpselectedbandsauxLabel")
        self.rpLabel = self.findChild(QtWidgets.QLabel, "rpLabel")
        self.apLabel = self.findChild(QtWidgets.QLabel, "apLabel")
        self.mfLabel = self.findChild(QtWidgets.QLabel, "mfLabel")
        self.seLabel = self.findChild(QtWidgets.QLabel, "seLabel")
        self.rpButton = self.findChild(QtWidgets.QPushButton, "rpButton")
        self.apButton = self.findChild(QtWidgets.QPushButton, "apButton")
        self.mfButton = self.findChild(QtWidgets.QPushButton, "mfButton")
        self.seButton = self.findChild(QtWidgets.QPushButton, "seButton")
        # Element setup
        for widget in [self.rpselectedbandsLabel, self.apselectedbandsLabel, self.mfselectedbandsLabel,
                       self.seselectedbandsLabel, self.rpselectedbandsauxLabel, self.mfLabel, self.seLabel,
                       self.rpLabel, self.apLabel, self.rpButton, self.apButton, self.mfButton, self.seButton]:
            widget.setVisible(False)
        self.rpCBox.toggled.connect(self.toggle_relative_power)
        self.apCBox.toggled.connect(self.toggle_absolute_power)
        self.mfCBox.toggled.connect(self.toggle_median_frequency)
        self.seCBox.toggled.connect(self.toggle_spectral_entropy)
        self.rpButton.clicked.connect(lambda: self.open_band_table("rp"))
        self.apButton.clicked.connect(lambda: self.open_band_table("ap"))
        self.mfButton.clicked.connect(lambda: self.open_band_table("mf"))
        self.seButton.clicked.connect(lambda: self.open_band_table("se"))

        # STATISTICS AND NONLINEAR
        self.meanCBox = self.findChild(QtWidgets.QCheckBox, "meanCBox")
        self.medianCBox = self.findChild(QtWidgets.QCheckBox, "medianCBox")
        self.varianceCBox = self.findChild(QtWidgets.QCheckBox, "varianceCBox")
        self.kurtosisCBox = self.findChild(QtWidgets.QCheckBox, "kurtosisCBox")
        self.skewnessCBox = self.findChild(QtWidgets.QCheckBox, "skewnessCBox")
        self.psdCBox = self.findChild(QtWidgets.QCheckBox, "psdCBox")
        self.segmentpsdLabel = self.findChild(QtWidgets.QLabel, "segmentpsdLabel")
        self.segmentpsdBox = self.findChild(QtWidgets.QSpinBox, "segmentpsdBox")
        self.overlappsdLabel = self.findChild(QtWidgets.QLabel, "overlappsdLabel")
        self.overlappsdBox = self.findChild(QtWidgets.QSpinBox, "overlappsdBox")
        self.windowpsdLabel = self.findChild(QtWidgets.QLabel, "windowpsdLabel")
        self.psdcomboBox = self.findChild(QtWidgets.QComboBox, "psdcomboBox")
        self.mfCBox = self.findChild(QtWidgets.QCheckBox, "mfCBox")
        self.seCBox = self.findChild(QtWidgets.QCheckBox, "seCBox")
        self.ctmCBox = self.findChild(QtWidgets.QCheckBox, "ctmCBox")
        self.ctmrLabel = self.findChild(QtWidgets.QLabel, "ctmrLabel")
        self.ctmrBox = self.findChild(QtWidgets.QDoubleSpinBox, "ctmrBox")
        self.sampenCBox = self.findChild(QtWidgets.QCheckBox, "sampenCBox")
        self.sampenmLabel = self.findChild(QtWidgets.QLabel, "sampenmLabel")
        self.sampenmBox = self.findChild(QtWidgets.QSpinBox, "sampenmBox")
        self.sampenrLabel = self.findChild(QtWidgets.QLabel, "sampenrLabel")
        self.sampenrBox = self.findChild(QtWidgets.QDoubleSpinBox, "sampenrBox")
        self.msampenCBox = self.findChild(QtWidgets.QCheckBox, "msampenCBox")
        self.maxscaleLabel = self.findChild(QtWidgets.QLabel, "maxscaleLabel")
        self.msampenscaleBox = self.findChild(QtWidgets.QSpinBox, "msampenscaleBox")
        self.msampenmLabel = self.findChild(QtWidgets.QLabel, "msampenmLabel")
        self.msampenmBox = self.findChild(QtWidgets.QSpinBox, "msampenmBox")
        self.msampenrLabel = self.findChild(QtWidgets.QLabel, "msampenrLabel")
        self.msampenrBox = self.findChild(QtWidgets.QDoubleSpinBox, "msampenrBox")
        self.lzcCBox = self.findChild(QtWidgets.QCheckBox, "lzcCBox")
        self.mlzcCBox = self.findChild(QtWidgets.QCheckBox, "mlzcCBox")
        self.mlzcscalesLabel = self.findChild(QtWidgets.QLabel, "mlzcscalesLabel")
        self.mlzcEdit = self.findChild(QtWidgets.QLineEdit, "mlzcEdit")
        # Element setup
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


    # %% --------------------------------------------- CONNECTIVITY  ------------------------------------------- #
        self.iacCBox = self.findChild(QtWidgets.QCheckBox, "iacCBox")
        self.iacortButton =self.findChild(QtWidgets.QCheckBox, "iacortButton")
        self.iacortLabel = self.findChild(QtWidgets.QLabel, "iacortLabel")
        self.aecCBox = self.findChild(QtWidgets.QCheckBox, "aecCBox")
        self.aecortLabel = self.findChild(QtWidgets.QLabel, "aecortLabel")
        self.aecortButton = self.findChild(QtWidgets.QCheckBox, "aecortButton")
        self.pliCBox = self.findChild(QtWidgets.QCheckBox, "pliCBox")
        self.plvCBox = self.findChild(QtWidgets.QCheckBox, "plvCBox")
        self.wpliCBox = self.findChild(QtWidgets.QCheckBox, "wpliCBox")
        # Element setup
        for widget in [self.iacortLabel, self.iacortButton, self.aecortLabel, self.aecortButton]:
            widget.setVisible(False)
        self.aecCBox.toggled.connect(self.toggle_aec)
        self.iacCBox.toggled.connect(self.toggle_iac)
    #%% DEFAULT VALUES
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
        for widget in [self.rpselectedbandsLabel, self.rpselectedbandsauxLabel, self.rpLabel, self.rpButton]:
            widget.setVisible(visible)

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

    def toggle_absolute_power(self):
        """
            Manages the visibility of the AP config parameters
        """
        visible = self.apCBox.isChecked()
        for widget in [self.apselectedbandsLabel, self.apLabel, self.apButton]:
            widget.setVisible(visible)
        if not visible:
            self.apLabel.setText("None")
            self.ap_band_editor = None
            self.selected_bands_by_type["ap"] = []
        else:
            broadband = {
                "name": "broadband",
                "min": self.main_window.preproc_config["broadband_min"],
                "max": self.main_window.preproc_config["broadband_max"],
            }
            self.selected_bands_by_type["ap"] = [broadband]
            self.apLabel.setText(f"broadband ({broadband['min']}–{broadband['max']} Hz)")

    def toggle_median_frequency(self):
        """
            Manages the visibility of the MF config parameters
        """
        visible = self.mfCBox.isChecked()
        for widget in [self.mfselectedbandsLabel, self.mfLabel, self.mfButton]:
            widget.setVisible(visible)
        if not visible:
            self.mfLabel.setText("None")
            self.mf_band_editor = None
            self.selected_bands_by_type["mf"] = []
        else:
            broadband = {
                "name": "broadband",
                "min": self.main_window.preproc_config["broadband_min"],
                "max": self.main_window.preproc_config["broadband_max"],
            }
            self.selected_bands_by_type["mf"] = [broadband]
            self.mfLabel.setText(f"broadband ({broadband['min']}–{broadband['max']} Hz)")

    def toggle_spectral_entropy(self):
        """
            Manages the visibility of the SE config parameters
        """
        visible = self.seCBox.isChecked()
        for widget in [self.seselectedbandsLabel, self.seLabel, self.seButton]:
            widget.setVisible(visible)
        if not visible:
            self.seLabel.setText("None")
            self.se_band_editor = None
            self.selected_bands_by_type["se"] = []
        else:
            broadband = {
                "name": "broadband",
                "min": self.main_window.preproc_config["broadband_min"],
                "max": self.main_window.preproc_config["broadband_max"],
            }
            self.selected_bands_by_type["se"] = [broadband]
            self.seLabel.setText(f"broadband ({broadband['min']}–{broadband['max']} Hz)")

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

    def _init_default_bands(self):
        """
        Initialize broadband (min_broad–max_broad).
        """
        default_band = {
            "name": "broadband",
            "min": self.main_window.preproc_config["broadband_min"],
            "max": self.main_window.preproc_config["broadband_max"],
        }
        for band_type in self.selected_bands_by_type.keys():
            self.selected_bands_by_type[band_type] = [default_band.copy()]
            label = getattr(self, f"{band_type}Label", None)
            if label:
                label.setText(f"broadband ({default_band['min']}–{default_band['max']} Hz)")

    # Additional functions for band table management
    def _on_band_table_closed(self, band_type):
        if band_type in self.band_table_editors:
            self.band_table_editors[band_type] = None

    def update_band_label(self, band_type, bands):
        broadband = {
            "name": "broadband",
            "min": self.main_window.preproc_config["broadband_min"],
            "max": self.main_window.preproc_config["broadband_max"],
        }
        print(self.main_window.preproc_config["broadband_max"])

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
            "selected_ap_bands": self.selected_bands_by_type["ap"] if self.apCBox.isChecked() else None,
            "median_frequency": True if self.mfCBox.isChecked() else None,
            "selected_mf_bands": self.selected_bands_by_type["mf"] if self.mfCBox.isChecked() else None,
            "spectral_entropy": True if self.seCBox.isChecked() else None,
            "selected_se_bands": self.selected_bands_by_type["se"] if self.seCBox.isChecked() else None,
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
