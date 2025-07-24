from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt
from bands_table import BandTable
from rp_bands_table import RPBandTable
from ap_bands_table import APBandTable
from mf_bands_table import MFBandTable
from se_bands_table import SEBandTable
from theme import PALETTE
import ast

class ParametersWidget(QtWidgets.QWidget):
    def __init__(self, main_window):
        super().__init__()

        self.main_window = main_window
        self.initialized = False  # Para que manejar los parámetros por defecto
        self.last_params = None

        uic.loadUi('parameters.ui', self)

        #%% ------------------------------------ BAND SEGMENTATION PAGE ----------------------------------------- #

        # Groupbox buttons and labels
        self.broadbandLabel = self.findChild(QtWidgets.QLabel, "broadbandLabel")
        self.minbroadBox = self.findChild(QtWidgets.QDoubleSpinBox, "minbroadBox")
        self.broadbandauxLabel = self.findChild(QtWidgets.QLabel, "broadbandauxLabel")
        self.maxbroadBox = self.findChild(QtWidgets.QDoubleSpinBox, "maxbroadBox")
        self.hzbroadbandLabel = self.findChild(QtWidgets.QLabel, "hzbroadbandLabel")
        self.bandCBox = self.findChild(QtWidgets.QCheckBox, "bandCBox")
        self.selectedbandsLabel = self.findChild(QtWidgets.QLabel, "selectedbandsLabel")
        self.selectedbandsauxLabel = self.findChild(QtWidgets.QLabel, "selectedbandsauxLabel")
        self.bandLabel = self.findChild(QtWidgets.QLabel, "bandLabel")
        self.bandButton = self.findChild(QtWidgets.QPushButton, "bandButton")

        # Group buttons connections
        self.bandCBox.toggled.connect(self.toggle_bands_segmentation)
        for widget in [self.selectedbandsLabel, self.selectedbandsauxLabel, self.bandLabel, self.bandButton]:
            widget.setVisible(False)
        self.bandButton.clicked.connect(self.open_band_editor)
        self.selected_bands = []
        self.band_editor = None  # se inicializa después

        # Sincronizar cambios en spinboxes con tabla si se abre
        self.minbroadBox.valueChanged.connect(self._sync_broadband_spinboxes)
        self.maxbroadBox.valueChanged.connect(self._sync_broadband_spinboxes)
        self.maxbroadBox.editingFinished.connect(self.validate_broadband_interval)

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
        self.iacyesRButton =self.findChild(QtWidgets.QRadioButton, "iacyesRButton")
        self.iacnoRButton = self.findChild(QtWidgets.QRadioButton, "iacnoRButton")
        self.iacortLabel = self.findChild(QtWidgets.QLabel, "iacortLabel")
        self.aecyesRButton = self.findChild(QtWidgets.QRadioButton, "aecyesRButton")
        self.aecnoRButton = self.findChild(QtWidgets.QRadioButton, "aecnoRButton")
        self.aecCBox = self.findChild(QtWidgets.QCheckBox, "aecCBox")
        self.aecortLabel = self.findChild(QtWidgets.QLabel, "aecortLabel")
        self.aecCBox.toggled.connect(self.toggle_aec)
        self.pliCBox = self.findChild(QtWidgets.QCheckBox, "pliCBox")
        self.plvCBox = self.findChild(QtWidgets.QCheckBox, "plvCBox")
        self.wpliCBox = self.findChild(QtWidgets.QCheckBox, "wpliCBox")

        for widget in [self.iacortLabel, self.iacyesRButton, self.iacnoRButton, self.aecortLabel,
                       self.aecnoRButton, self.aecyesRButton]:
            widget.setVisible(False)



    #%% Funciones comunes
    def get_parameters_config(self):
        # Configuración base
        config = {
            "band_segmentation": True if self.bandCBox.isChecked() else None,
            "broadband_min": self.minbroadBox.value(),
            "broadband_max": self.maxbroadBox.value(),
            "selected_bands": self.selected_bands if self.bandCBox.isChecked() else None,
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
            "ort_iac": True if self.iacyesRButton.isChecked() and self.iacCBox.isChecked() else None,
            "aec": True if self.aecCBox.isChecked() else None,
            "ort_aec": True if self.aecyesRButton.isChecked() and self.aecCBox.isChecked() else None,
            "pli": True if self.pliCBox.isChecked() else None,
            "plv": True if self.plvCBox.isChecked() else None,
            "wpli": True if self.wpliCBox.isChecked() else None,

        }

        return config
    #%% Funciones de bands segmentation
    def validate_broadband_interval(self):

        start = self.minbroadBox.value()
        end = self.maxbroadBox.value()

        # Validación
        if end <= start:
            # Bloquear señales para prevenir loops
            self.minbroadBox.blockSignals(True)
            self.maxbroadBox.blockSignals(True)

            QtWidgets.QMessageBox.warning(
                self,
                "Invalid Broadband range",
                "Max. frequency must be greater than min. frequency."
            )

            self.minbroadBox.setValue(getattr(self, "default_min_broad", 0.5))
            self.maxbroadBox.setValue(getattr(self, "default_max_broad", 70))

            # Desbloquear señales
            self.minbroadBox.blockSignals(False)
            self.maxbroadBox.blockSignals(False)

    def set_defaults_from_preprocessing(self, params):
        if not self.initialized or self._params_changed(params):
            if params.get("bandpass"):
                self.default_min_broad = params.get("bp_min", 0)
                self.default_max_broad = params.get("bp_max", 70)
            elif params.get("resample"):
                self.default_min_broad = 0.5
                self.default_max_broad = params.get("resample_fs", 70)
            else:
                self.default_min_broad = 0.5
                self.default_max_broad = 70  # TO DO: usar fs/2 si lo tienes

            self.minbroadBox.setValue(self.default_min_broad)
            self.maxbroadBox.setValue(self.default_max_broad)

            self.last_params = dict(params)
            self.initialized = True

    def _params_changed(self, new_params):
        # Si nunca se guardaron params, han cambiado
        if self.last_params is None:
            return True
        # Comparamos claves relevantes
        keys_to_check = ["bandpass", "bp_min", "bp_max"]
        return any(self.last_params.get(k) != new_params.get(k) for k in keys_to_check)

    def toggle_bands_segmentation(self):
        '''
        Función para mostrar los datos relacionados con las bandas en caso de marcar que si que se desea hacer
        segmenatación por bandas. Si se desmarca el CheckBoxButton, se ocultan los datos.
        '''
        visible = self.bandCBox.isChecked()
        for widget in [self.selectedbandsLabel, self.selectedbandsauxLabel, self.bandLabel, self.bandButton]:
            widget.setVisible(visible)
    def open_band_editor(self):
        if self.band_editor is None:
            self.band_editor = BandTable(
                parameters_widget=self,
                min_broad=self.minbroadBox.value(),
                max_broad=self.maxbroadBox.value()
            )
            self.band_editor.setModal(True)  # Hace que desactive MainWindow sin cerrar herencia
            self.band_editor.show()
        else:
            self.band_editor.sync_broadband_range(
                self.minbroadBox.value(),
                self.maxbroadBox.value()
            )
        self.band_editor.show()

    def update_band_label(self, bands):
        self.selected_bands = bands
        if bands:
            names = [b["name"] for b in bands]
            self.bandLabel.setText(", ".join(names))
        else:
            self.bandLabel.setText("None")

    def _sync_broadband_spinboxes(self):
        if self.band_editor:
            self.band_editor.sync_broadband_range(
                self.minbroadBox.value(),
                self.maxbroadBox.value()
            )

    def update_broadband_spinboxes(self, min_val, max_val):
        self.minbroadBox.blockSignals(True)
        self.maxbroadBox.blockSignals(True)
        self.minbroadBox.setValue(min_val)
        self.maxbroadBox.setValue(max_val)
        self.minbroadBox.blockSignals(False)
        self.maxbroadBox.blockSignals(False)

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

        if visible:
            msg_box = QtWidgets.QMessageBox(self)
            msg_box.setIcon(QtWidgets.QMessageBox.Warning)
            msg_box.setWindowTitle("Relative Power Warning")
            msg_box.setTextFormat(Qt.RichText)
            msg_box.setText(
                "<b>Relative Power is normalized</b> using the selected broadband range.<br><br>"
                "You can adjust this range in the <i><b>Band segmentation</b></i> section."
            )
            msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
            msg_box.exec_()

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

        if not visible:
            # Resetear selección solo si se desactiva la casilla
            self.iacyesRButton.setAutoExclusive(False)
            self.iacnoRButton.setAutoExclusive(False)
            self.iacyesRButton.setChecked(False)
            self.iacnoRButton.setChecked(False)
            self.iacyesRButton.setAutoExclusive(True)
            self.iacnoRButton.setAutoExclusive(True)

        for widget in [self.iacortLabel, self.iacyesRButton, self.iacnoRButton]:
            widget.setVisible(visible)

    def toggle_aec(self):
        visible = self.aecCBox.isChecked()
        if not visible:
            # Resetear selección solo si se desactiva la casilla
            self.aecyesRButton.setAutoExclusive(False)
            self.aecnoRButton.setAutoExclusive(False)
            self.aecyesRButton.setChecked(False)
            self.aecnoRButton.setChecked(False)
            self.aecyesRButton.setAutoExclusive(True)
            self.aecnoRButton.setAutoExclusive(True)
        for widget in [self.aecortLabel, self.aecyesRButton, self.aecnoRButton]:
            widget.setVisible(visible)