from PyQt5 import QtWidgets, uic, QtCore
from Parameters.rp_bands_table import RPBandTable
from Parameters.ap_bands_table import APBandTable
from Parameters.mf_bands_table import MFBandTable
from Parameters.se_bands_table import SEBandTable
import ast

class ParametersWidget(QtWidgets.QWidget):
    def __init__(self, main_window):
        super().__init__()

        self.main_window = main_window
        self.last_params = None

        uic.loadUi('Parameters/parameters_widget.ui', self)

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
                    recordings, including band-based metrics. statistical descriptors, spectral features, 
                    non-lineal parameters and connectivity metrics.
                </p>
                <p>
                    Use the checkboxes to enable the metrics of interest. Some metrics require specific 
                    band selections or additional parameters, which can be adjusted after activation.
                </p>
            </div>
        """)
        layout.addWidget(self.logtextBrowser)


        #%% --------------------------------------------- SIGNAL METRICS  ------------------------------------------- #
        # RP and AP
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

        self.rpCBox.toggled.connect(self.toggle_relative_power)
        self.apCBox.toggled.connect(self.toggle_absolute_power)
        self.mfCBox.toggled.connect(self.toggle_median_frequency)
        self.seCBox.toggled.connect(self.toggle_spectral_entropy)
        for widget in [self.rpselectedbandsLabel, self.apselectedbandsLabel, self.mfselectedbandsLabel,
                       self.seselectedbandsLabel, self.rpselectedbandsauxLabel, self.mfLabel, self.seLabel,
                       self.rpLabel, self.apLabel, self.rpButton, self.apButton, self.mfButton, self.seButton]:
            widget.setVisible(False)
        self.rpButton.clicked.connect(self.open_rp_band_table)
        self.apButton.clicked.connect(self.open_ap_band_table)
        self.mfButton.clicked.connect(self.open_mf_band_table)
        self.seButton.clicked.connect(self.open_se_band_table)
        self.selected_rp_bands = []
        self.selected_ap_bands = []
        self.selected_mf_bands = []
        self.selected_se_bands = []
        self.rp_band_editor = None
        self.ap_band_editor = None
        self.mf_band_editor = None
        self.se_band_editor = None

        self.meanCBox = self.findChild(QtWidgets.QCheckBox, "meanCBox")
        self.medianCBox = self.findChild(QtWidgets.QCheckBox, "medianCBox")
        self.varianceCBox = self.findChild(QtWidgets.QCheckBox, "varianceCBox")
        self.kurtosisCBox = self.findChild(QtWidgets.QCheckBox, "kurtosisCBox")
        self.skewnessCBox = self.findChild(QtWidgets.QCheckBox, "skewnessCBox")
        self.psdCBox = self.findChild(QtWidgets.QCheckBox, "psdCBox")
        self.psdCBox.toggled.connect(self.toggle_psd)
        self.segmentpsdLabel = self.findChild(QtWidgets.QLabel, "segmentpsdLabel")
        self.segmentpsdBox = self.findChild(QtWidgets.QSpinBox, "segmentpsdBox")
        self.overlappsdLabel = self.findChild(QtWidgets.QLabel, "overlappsdLabel")
        self.overlappsdBox = self.findChild(QtWidgets.QSpinBox, "overlappsdBox")
        self.windowpsdLabel = self.findChild(QtWidgets.QLabel, "windowpsdLabel")
        self.psdcomboBox = self.findChild(QtWidgets.QComboBox, "psdcomboBox")
        self.mfCBox = self.findChild(QtWidgets.QCheckBox, "mfCBox")
        self.seCBox = self.findChild(QtWidgets.QCheckBox, "seCBox")
        self.ctmCBox = self.findChild(QtWidgets.QCheckBox, "ctmCBox")
        self.ctmCBox.toggled.connect(self.toggle_ctm)
        self.ctmrLabel = self.findChild(QtWidgets.QLabel, "ctmrLabel")
        self.ctmrBox = self.findChild(QtWidgets.QDoubleSpinBox, "ctmrBox")
        self.sampenCBox = self.findChild(QtWidgets.QCheckBox, "sampenCBox")
        self.sampenCBox.toggled.connect(self.toggle_sampen)
        self.sampenmLabel = self.findChild(QtWidgets.QLabel, "sampenmLabel")
        self.sampenmBox = self.findChild(QtWidgets.QSpinBox, "sampenmBox")
        self.sampenrLabel = self.findChild(QtWidgets.QLabel, "sampenrLabel")
        self.sampenrBox = self.findChild(QtWidgets.QDoubleSpinBox, "sampenrBox")
        self.msampenCBox = self.findChild(QtWidgets.QCheckBox, "msampenCBox")
        self.msampenCBox.toggled.connect(self.toggle_msampen)
        self.maxscaleLabel = self.findChild(QtWidgets.QLabel, "maxscaleLabel")
        self.msampenscaleBox = self.findChild(QtWidgets.QSpinBox, "msampenscaleBox")
        self.msampenmLabel = self.findChild(QtWidgets.QLabel, "msampenmLabel")
        self.msampenmBox = self.findChild(QtWidgets.QSpinBox, "msampenmBox")
        self.msampenrLabel = self.findChild(QtWidgets.QLabel, "msampenrLabel")
        self.msampenrBox = self.findChild(QtWidgets.QDoubleSpinBox, "msampenrBox")
        self.lzcCBox = self.findChild(QtWidgets.QCheckBox, "lzcCBox")
        self.mlzcCBox = self.findChild(QtWidgets.QCheckBox, "mlzcCBox")
        self.mlzcCBox.toggled.connect(self.toggle_mlzc)
        self.mlzcscalesLabel = self.findChild(QtWidgets.QLabel, "mlzcscalesLabel")
        self.mlzcEdit = self.findChild(QtWidgets.QLineEdit, "mlzcEdit")

        for widget in [self.ctmrLabel, self.ctmrBox, self.sampenmLabel, self.sampenmBox, self.sampenrLabel, self.sampenrBox,
                       self.maxscaleLabel, self.msampenscaleBox, self.msampenmLabel, self.msampenmBox, self.msampenrLabel,
                       self.msampenrBox, self.mlzcscalesLabel, self.mlzcEdit, self.windowpsdLabel,
                       self.psdcomboBox, self.overlappsdBox, self.segmentpsdBox, self.segmentpsdLabel, self.overlappsdLabel]:
            widget.setVisible(False)

    # %% --------------------------------------------- CONNECTIVITY  ------------------------------------------- #
        self.iacCBox = self.findChild(QtWidgets.QCheckBox, "iacCBox")
        self.iacCBox.toggled.connect(self.toggle_iac)
        self.iacortButton =self.findChild(QtWidgets.QCheckBox, "iacortButton")
        self.iacortLabel = self.findChild(QtWidgets.QLabel, "iacortLabel")
        self.aecCBox = self.findChild(QtWidgets.QCheckBox, "aecCBox")
        self.aecortLabel = self.findChild(QtWidgets.QLabel, "aecortLabel")
        self.aecortButton = self.findChild(QtWidgets.QCheckBox, "aecortButton")
        self.aecCBox.toggled.connect(self.toggle_aec)
        self.pliCBox = self.findChild(QtWidgets.QCheckBox, "pliCBox")
        self.plvCBox = self.findChild(QtWidgets.QCheckBox, "plvCBox")
        self.wpliCBox = self.findChild(QtWidgets.QCheckBox, "wpliCBox")

        for widget in [self.iacortLabel, self.iacortButton, self.aecortLabel, self.aecortButton]:
            widget.setVisible(False)


    #%% Funciones comunes
    def get_parameters_config(self):
        # Configuración base
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
            "selected_rp_bands": self.selected_rp_bands if self.rpCBox.isChecked() else None,
            "absolute_power": True if self.apCBox.isChecked() else None,
            "selected_ap_bands": self.selected_ap_bands if self.apCBox.isChecked() else None,
            "median_frequency": True if self.mfCBox.isChecked() else None,
            "selected_mf_bands": self.selected_mf_bands if self.mfCBox.isChecked() else None,
            "spectral_entropy": True if self.seCBox.isChecked() else None,
            "selected_se_bands": self.selected_se_bands if self.seCBox.isChecked() else None,
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
            "wpli": True if self.wpliCBox.isChecked() else None,

        }

        return config

    #%% Funciones de signal metrics
    def toggle_psd(self):
        visible = self.psdCBox.isChecked()
        for widget in [self.segmentpsdLabel, self.segmentpsdBox, self.overlappsdLabel, self.overlappsdBox,
                       self.psdcomboBox, self.windowpsdLabel]:
            widget.setVisible(visible)

    def toggle_relative_power(self):
        '''
        Función para mostrar los datos relacionados con las bandas en caso de marcar que si que se desea hacer
        segmenatación por bandas. Si se desmarca el CheckBoxButton, se ocultan los datos.
        '''
        visible = self.rpCBox.isChecked()
        for widget in [self.rpselectedbandsLabel, self.rpselectedbandsauxLabel, self.rpLabel, self.rpButton]:
            widget.setVisible(visible)

        # if visible:
        #     msg_box = QtWidgets.QMessageBox(self)
        #     msg_box.setIcon(QtWidgets.QMessageBox.Warning)
        #     msg_box.setWindowTitle("Relative Power Warning")
        #     msg_box.setTextFormat(Qt.RichText)
        #     msg_box.setText(
        #         "<b>Relative Power is normalized</b> using the selected broadband range.<br><br>"
        #         "You can adjust this range in the <i><b>Band segmentation</b></i> section."
        #     )
        #     msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        #     msg_box.exec_()

    def toggle_absolute_power(self):
        '''
        Función para mostrar los datos relacionados con las bandas en caso de marcar que si que se desea hacer
        segmenatación por bandas. Si se desmarca el CheckBoxButton, se ocultan los datos.
        '''
        visible = self.apCBox.isChecked()
        for widget in [self.apselectedbandsLabel, self.apLabel, self.apButton]:
            widget.setVisible(visible)

    def toggle_median_frequency(self):
        '''
        Función para mostrar los datos relacionados con las bandas en caso de marcar que si que se desea hacer
        segmenatación por bandas. Si se desmarca el CheckBoxButton, se ocultan los datos.
        '''
        visible = self.mfCBox.isChecked()
        for widget in [self.mfselectedbandsLabel, self.mfLabel, self.mfButton]:
            widget.setVisible(visible)

    def toggle_spectral_entropy(self):
        '''
        Función para mostrar los datos relacionados con las bandas en caso de marcar que si que se desea hacer
        segmenatación por bandas. Si se desmarca el CheckBoxButton, se ocultan los datos.
        '''
        visible = self.seCBox.isChecked()
        for widget in [self.seselectedbandsLabel, self.seLabel, self.seButton]:
            widget.setVisible(visible)

    def open_rp_band_table(self):
        if self.rp_band_editor is None:
            self.rp_band_editor = RPBandTable(
                parameters_widget=self
            )
            self.rp_band_editor.setModal(True)
            self.rp_band_editor.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.rp_band_editor.destroyed.connect(lambda: self._on_rp_band_editor_closed())
            self.rp_band_editor.show()

    def open_ap_band_table(self):
        if self.ap_band_editor is None:
            self.ap_band_editor = APBandTable(
                parameters_widget=self
            )
            self.ap_band_editor.setModal(True)
            self.ap_band_editor.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.ap_band_editor.destroyed.connect(lambda: self._on_ap_band_editor_closed())
            self.ap_band_editor.show()

    def open_mf_band_table(self):
        if self.mf_band_editor is None:
            self.mf_band_editor = MFBandTable(
                parameters_widget=self
            )
            self.mf_band_editor.setModal(True)
            self.mf_band_editor.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.mf_band_editor.destroyed.connect(lambda: self._on_mf_band_editor_closed())
            self.mf_band_editor.show()

    def open_se_band_table(self):
        if self.se_band_editor is None:
            self.se_band_editor = SEBandTable(
                parameters_widget=self
            )
            self.se_band_editor.setModal(True)
            self.se_band_editor.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            self.se_band_editor.destroyed.connect(lambda: self._on_se_band_editor_closed())
            self.se_band_editor.show()

    def _on_rp_band_editor_closed(self):
        self.rp_band_editor = None
    def _on_ap_band_editor_closed(self):
        self.ap_band_editor = None
    def _on_mf_band_editor_closed(self):
        self.mf_band_editor = None
    def _on_se_band_editor_closed(self):
        self.se_band_editor = None

    def update_band_rp_label(self, rp_bands):
        self.selected_rp_bands = rp_bands
        if rp_bands:
            names = [b["name"] for b in rp_bands]
            self.rpLabel.setText(", ".join(names))
        else:
            self.rpLabel.setText("None")

    def update_band_ap_label(self, ap_bands):
        self.selected_ap_bands = ap_bands
        if ap_bands:
            names = [b["name"] for b in ap_bands]
            self.apLabel.setText(", ".join(names))
        else:
            self.apLabel.setText("None")

    def update_band_mf_label(self, mf_bands):
        self.selected_mf_bands = mf_bands
        if mf_bands:
            names = [b["name"] for b in mf_bands]
            self.mfLabel.setText(", ".join(names))
        else:
            self.mfLabel.setText("None")

    def update_band_se_label(self, se_bands):
        self.selected_se_bands = se_bands
        if se_bands:
            names = [b["name"] for b in se_bands]
            self.seLabel.setText(", ".join(names))
        else:
            self.seLabel.setText("None")

    def toggle_ctm(self):
        '''
        Función para mostrar los datos relacionados con la CTM. Si se desmarca el CheckBoxButton, se ocultan los datos.
        '''
        visible = self.ctmCBox.isChecked()
        for widget in [self.ctmrLabel, self.ctmrBox]:
            widget.setVisible(visible)

    def toggle_sampen(self):
        '''
        Función para mostrar los datos relacionados con la CTM. Si se desmarca el CheckBoxButton, se ocultan los datos.
        '''
        visible = self.sampenCBox.isChecked()
        for widget in [self.sampenmLabel, self.sampenmBox, self.sampenrLabel, self.sampenrBox]:
            widget.setVisible(visible)

    def toggle_msampen(self):
        '''
        Función para mostrar los datos relacionados con la CTM. Si se desmarca el CheckBoxButton, se ocultan los datos.
        '''
        visible = self.msampenCBox.isChecked()
        for widget in [self.maxscaleLabel, self.msampenscaleBox, self.msampenmLabel, self.msampenmBox,
                       self.msampenrLabel, self.msampenrBox]:
            widget.setVisible(visible)

    def toggle_mlzc(self):
        '''
        Function to show/hide data related to CTM. If the CheckBoxButton is unchecked, the data is hidden.
        Also validates values entered in mlzcEdit.
        '''
        visible = self.mlzcCBox.isChecked()
        for widget in [self.mlzcscalesLabel, self.mlzcEdit]:
            widget.setVisible(visible)

    def toggle_iac(self):
        visible = self.iacCBox.isChecked()
        if visible: self.iacortButton.setChecked(True)
        else: self.iacyesButton.setChecked(False)
        for widget in [self.iacortLabel, self.iacortButton]:
            widget.setVisible(visible)

    def toggle_aec(self):
        visible = self.aecCBox.isChecked()
        if visible: self.aecortButton.setChecked(True)
        else: self.aecortButton.setChecked(False)
        for widget in [self.aecortLabel, self.aecortButton]:
            widget.setVisible(visible)