from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from files_list_dialog import FilesListDialog

class PreprocessingWidget(QtWidgets.QWidget):
    def __init__(self, main_window):
        super().__init__()

        self.main_window = main_window
        self.validating_bandpass = False
        self.validating_notch = False
        # self.apply_custom_styles()

        uic.loadUi("preprocessing.ui", self)

        # -----------------                   GROUPBOX: Data loading                                      ------------#
        self.browseButton = self.findChild(QtWidgets.QPushButton, "browseButton")
        self.deletefilesButton = self.findChild(QtWidgets.QPushButton, "deletefilesButton")
        self.viewfilesButton = self.findChild(QtWidgets.QPushButton, "viewfilesButton")
        self.selectLabel = self.findChild(QtWidgets.QLabel, "selectLabel")
        self.selected_files = []  # Almacena las rutas de los archivos seleccionados

        self.browseButton.clicked.connect(self.select_files)
        self.deletefilesButton.clicked.connect(self.delete_files)
        self.viewfilesButton.clicked.connect(self.open_file_list_dialog)

        # -----------------                   GROUPBOX: Data preprocessing                                ------------#
        self.yesRButton = self.findChild(QtWidgets.QRadioButton, "yesRButton")
        self.noRButton = self.findChild(QtWidgets.QRadioButton, "noRButton")
        # Hacemos que de primeras ambos botones aparezcan desactivados hasta que el usuario seleccione archivos.
        self.yesRButton.setDisabled(True)
        self.noRButton.setDisabled(True)

        # ======================================== Notch ========================================================= #
        self.notchLabel = self.findChild(QtWidgets.QLabel, "notchfilterLabel")
        self.notchCBox = self.findChild(QtWidgets.QCheckBox, "notchCBox")
        self.notchminLabel = self.findChild(QtWidgets.QLabel, "notchminLabel")
        self.minfreqnotchBox = self.findChild(QtWidgets.QDoubleSpinBox, "minfreqnotchBox")
        self.notchmaxLabel = self.findChild(QtWidgets.QLabel, "notchmaxLabel")
        self.maxfreqnotchBox = self.findChild(QtWidgets.QDoubleSpinBox, "maxfreqnotchBox")
        self.orderNotchLabel = self.findChild(QtWidgets.QLabel, "orderNotchLabel")
        self.orderNotchBox = self.findChild(QtWidgets.QSpinBox, "orderNotchBox")

        # ======================================== Bandpass ========================================================= #
        self.bpLabel = self.findChild(QtWidgets.QLabel, "bpLabel")
        self.bpCBox = self.findChild(QtWidgets.QCheckBox, "bpCBox")
        self.bpminLabel = self.findChild(QtWidgets.QLabel, "bpminfreqLabel")
        self.minfreqbpBox = self.findChild(QtWidgets.QDoubleSpinBox, "minfreqbpBox")
        self.bpmaxLabel = self.findChild(QtWidgets.QLabel, "bpmaxfreqLabel")
        self.maxfreqbpBox = self.findChild(QtWidgets.QDoubleSpinBox, "maxfreqbpBox")
        self.orderbpLabel = self.findChild(QtWidgets.QLabel, "orderbpLabel")
        self.orderbpBox = self.findChild(QtWidgets.QSpinBox, "orderbpBox")

        # ======================================== CAR ========================================================= #
        self.carLabel = self.findChild(QtWidgets.QLabel, "carLabel")
        self.carCBox = self.findChild(QtWidgets.QCheckBox, "carCBox")

        # Group buttons connection
        self.yesRButton.toggled.connect(self.toggle_preprocessing_group)
        self.noRButton.toggled.connect(self.toggle_preprocessing_group)
        self.notchCBox.toggled.connect(self.toggle_notch_controls)
        self.bpCBox.toggled.connect(self.toggle_bandpass_controls)

        # Inicializar estado
        self.reset_all_controls()
        self.maxfreqbpBox.editingFinished.connect(self.validate_bandpass_bounds)
        self.maxfreqnotchBox.editingFinished.connect(self.validate_notch_bounds)
        self.main_window.selected_files = self.selected_files

    def reset_all_controls(self):
        '''
        Esta función oculta todos los elementos del groupbox de data preprocessing y pone sus valores por defecto.
        Se llama:
            - Al inicio, la primera vez que se ejecuta el Analyzer.
            - Cuando se elige "no" al preprocesamiento.
            - Cuando se borran los archivos (pulsando en 'delete files' o bien desde dentro de 'View list'.
        '''

        for w in [
            self.notchLabel, self.notchCBox, self.notchminLabel, self.minfreqnotchBox, self.notchmaxLabel, self.maxfreqnotchBox, self.orderNotchLabel, self.orderNotchBox,
            self.bpLabel, self.bpCBox, self.bpminLabel, self.minfreqbpBox, self.bpmaxLabel, self.maxfreqbpBox, self.orderbpLabel, self.orderbpBox,
            self.carLabel, self.carCBox,
        ]:
            w.setVisible(False)

        # Resetear los checkboxes para que no estén marcadas
        for box in [self.notchCBox, self.bpCBox, self.carCBox, self.yesRButton,
            self.noRButton,
        ]:
            box.setChecked(False)

        # Reseteamos todas las spinboxes para poner sus valores por defecto
        self.minfreqnotchBox.setValue(self.minfreqnotchBox.minimum())
        self.maxfreqnotchBox.setValue(self.maxfreqnotchBox.minimum())
        self.orderNotchBox.setValue(self.orderNotchBox.minimum())
        self.minfreqbpBox.setValue(self.minfreqbpBox.minimum())
        self.maxfreqbpBox.setValue(self.maxfreqbpBox.minimum())
        self.orderbpBox.setValue(self.orderbpBox.minimum())

    def select_files(self):
        """
        Función para seleccionar múltiples archivos de varias carpetas. Luego los guarda en 'self.selected_files'.
        Actualiza la etiqueta con el número de archivos.
        Habilita los radialButtons para el preprocesamiento (dentro de 'update_selected_label()').
        """
        files, _ = QFileDialog.getOpenFileNames(self, "Seleccionar archivos de señal", "", "Todos los archivos (*.bson; *.json)")
        if files:
            self.selected_files.extend(files)
            self.update_select_label()

    def delete_files(self):
        """
        Función para eliminar todos los archivos seleccionados tras confirmar con el usuario.
        Después oculta los botones.
        """
        if not self.selected_files:
            return
        reply = QMessageBox.question(self, "Eliminar archivos", "¿Quieres eliminar todos los archivos seleccionados?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.selected_files = []
            self.update_select_label()
            self.reset_all_controls() # ocular y poner a los valores por defecto los controles

    def update_select_label(self):
        '''
        Función para actualizar el texto con el número de archivos seleccionados.
        IMPORTANTE: Habilita y deshabilita los radioButtons y el botón de siguiente en función de si hay archivos
        seleccionados o no
        '''

        count = len(self.selected_files)
        self.selectLabel.setText(f"{count} archivos seleccionados")

        # Sincronizar con main_window
        self.main_window.selected_files = self.selected_files.copy()
        self.main_window.segmentation_widget.reset_segmentation_state()
        print(count)

        if count > 0: # sí que hay archivos entonces habilitamos los radioButtons
            self.yesRButton.setDisabled(False)
            self.noRButton.setDisabled(False)

            if self.yesRButton.isChecked() or self.noRButton.isChecked():
                self.main_window.nextButton.setDisabled(False)
            else:
                self.main_window.nextButton.setDisabled(True)

        else: # no hay archivos entonces deshabilitamos los botones y no dejamos pasar de página
            self.yesRButton.setDisabled(True)
            self.noRButton.setDisabled(True)

            # NOTA: el problema aquí es que al ser auto-excluyentes y deshabilitarlos se ve como uno de ellos siempre
            # va a quedar marcados. Por ello, hay que quitar un momento la auto-exclusividad, desmarcarlos, y volver
            # a activar la auto-exclusividad.
            self.yesRButton.setAutoExclusive(False)
            self.noRButton.setAutoExclusive(False)
            self.yesRButton.setChecked(False)
            self.noRButton.setChecked(False)
            self.yesRButton.setAutoExclusive(True)
            self.noRButton.setAutoExclusive(True)

            self.main_window.nextButton.setDisabled(True)

    def open_file_list_dialog(self):
        dialog = FilesListDialog(self.selected_files, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.selected_files = dialog.get_updated_files()
            self.update_select_label()

    def toggle_preprocessing_group(self):
        '''
        Esta función muestra u oculta los controles de preprocesamiento dependiendo de si el usuario elige
        aplicarlos o no. Además, ya activamos el botón de Next en la main_window.
        '''

        self.main_window.nextButton.setDisabled(False)
        if self.noRButton.isChecked():
            self.reset_all_controls()
            return

        if self.yesRButton.isChecked(): # mostramos los controles de preprocessing (pero siguen ocultos sus parámetros)
            pairs = [
                (self.notchLabel, self.notchCBox),
                (self.bpLabel, self.bpCBox),
                (self.carLabel, self.carCBox),
            ]

            for label, checkbox in pairs:
                label.setVisible(True)
                checkbox.setVisible(True)

    def toggle_notch_controls(self, checked):
        '''
                Muestra y oculta los parámetros asociados a 'notch_filyer' cuando se marca o se desmarca su checkbox principal.
                :param checked:
                '''
        self.notchminLabel.setVisible(checked)
        self.minfreqnotchBox.setVisible(checked)
        self.notchmaxLabel.setVisible(checked)
        self.maxfreqnotchBox.setVisible(checked)
        self.orderNotchLabel.setVisible(checked)
        self.orderNotchBox.setVisible(checked)

    def toggle_bandpass_controls(self, checked):
        '''
                Muestra y oculta los parámetros asociados a 'bandpass' cuando se marca o se desmarca su checkbox principal.
                :param checked:
                '''
        self.bpminLabel.setVisible(checked)
        self.minfreqbpBox.setVisible(checked)
        self.bpmaxLabel.setVisible(checked)
        self.maxfreqbpBox.setVisible(checked)
        self.orderbpLabel.setVisible(checked)
        self.orderbpBox.setVisible(checked)

    def validate_bandpass_bounds(self):
        if self.validating_bandpass:
            return

        self.validating_bandpass = True

        min_val = self.minfreqbpBox.value()
        max_val = self.maxfreqbpBox.value()
        min_limit = self.minfreqbpBox.minimum()
        max_limit = self.maxfreqbpBox.minimum()

        if max_val <= min_val:
            QMessageBox.warning(
                self,
                "Invalid values for bandpass filter.",
                f"For bandpass filtering, <b>max</b> frequency ({max_val}) must be greater than <b>min</b> ({min_val})."
            )

            self.minfreqbpBox.setValue(min_limit)
            self.maxfreqbpBox.setValue(max_limit)

        self.validating_bandpass = False

    def validate_notch_bounds(self):
        if self.validating_notch:
            return

        self.validating_notch = True

        min_val = self.minfreqnotchBox.value()
        max_val = self.maxfreqnotchBox.value()
        min_limit = self.minfreqnotchBox.minimum()
        max_limit = self.maxfreqnotchBox.minimum()

        if max_val <= min_val:
            QMessageBox.warning(
                self,
                "Invalid values for notch filter.",
                f"For notch filtering, <b>max</b> frequency ({max_val}) must be greater than <b>min</b> ({min_val})."
            )

            self.minfreqnotchBox.setValue(min_limit)
            self.maxfreqnotchBox.setValue(max_limit)

        self.validating_notch = False

    def get_preprocessing_config(self):
        config = {
            "selected_files": self.selected_files if self.selected_files else None,
            "apply_preprocessing": True if self.yesRButton.isChecked() else None,

            "notch": self.notchCBox.isChecked() if self.notchCBox else None,
            "notch_min": self.minfreqnotchBox.value() if self.notchCBox.isChecked() else None,
            "notch_max": self.maxfreqnotchBox.value() if self.notchCBox.isChecked() else None,
            "notch_order": self.orderNotchBox.value() if self.notchCBox.isChecked() else None,

            "bandpass": self.bpCBox.isChecked() if self.bpCBox else None,
            "bp_min": self.minfreqbpBox.value() if self.bpCBox.isChecked() else None,
            "bp_max": self.maxfreqbpBox.value() if self.bpCBox.isChecked() else None,
            "bp_order": self.orderbpBox.value() if self.bpCBox.isChecked() else None,

            "car": self.carCBox.isChecked() if self.carCBox else None,
        }
        return config
