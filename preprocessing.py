from PyQt5 import QtWidgets, uic, QtGui, QtCore
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from files_list_dialog import FilesListDialog
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy.signal import firwin, freqz
import numpy as np

class GradientTitleWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(50)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        font = QtGui.QFont("Arial", 36, QtGui.QFont.Bold)
        painter.setFont(font)

        text = "MEDUSA©-Analyzer"
        fm = QtGui.QFontMetrics(font)
        text_width = fm.width(text)

        x = (self.width() - text_width) // 2
        y = (self.height() + fm.ascent() - fm.descent()) // 2

        gradient = QtGui.QLinearGradient(x, 0, x + text_width, 0)
        gradient.setColorAt(0.0, QtGui.QColor("#6a0dad"))   # Morado
        gradient.setColorAt(1.0, QtGui.QColor("#ec407a"))   # Rosa

        brush = QtGui.QBrush(gradient)
        painter.setPen(QtGui.QPen(brush, 0))
        painter.drawText(x, y, text)

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=4, height=3, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

class PreprocessingWidget(QtWidgets.QWidget):
    def __init__(self, main_window):
        super().__init__()

        self.main_window = main_window
        self.validating_bandpass = False
        self.validating_notch = False

        uic.loadUi("preprocessing_modificated.ui", self)

        self.title_widget = GradientTitleWidget(self)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.title_widget)
        self.topContentWidget = self.findChild(QtWidgets.QWidget, "topContentWidget")
        self.topContentWidget.setLayout(layout)
        self.description_label = QtWidgets.QLabel()
        self.description_label.setTextFormat(QtCore.Qt.RichText)
        self.description_label.setWordWrap(True)
        self.description_label.setText("""
                <p style="font-size: 12pt; font-family: Arial;">
                Welcome to the <b>Preprocessing Module</b> of <i>MEDUSA Analyzer</i>. 
                Please select at least one <span style="color:#007acc; font-weight:bold;">.rec</span> file to begin.
                </p>
                """)
        layout.addWidget(self.description_label)

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
        self.preprocessingButton = self.findChild(QtWidgets.QCheckBox, "preprocessingButton")
        self.preprocessingButton.setChecked(True)

        # ======================================== Notch ========================================================= #
        self.notchgroupBox = self.findChild(QtWidgets.QGroupBox, "notchgroupBox")
        self.notchLabel = self.findChild(QtWidgets.QLabel, "notchfilterLabel")
        self.notchCBox = self.findChild(QtWidgets.QCheckBox, "notchCBox")
        self.notchminLabel = self.findChild(QtWidgets.QLabel, "notchminLabel")
        self.minfreqnotchBox = self.findChild(QtWidgets.QDoubleSpinBox, "minfreqnotchBox")
        self.notchmaxLabel = self.findChild(QtWidgets.QLabel, "notchmaxLabel")
        self.maxfreqnotchBox = self.findChild(QtWidgets.QDoubleSpinBox, "maxfreqnotchBox")
        self.orderNotchLabel = self.findChild(QtWidgets.QLabel, "orderNotchLabel")
        self.orderNotchBox = self.findChild(QtWidgets.QSpinBox, "orderNotchBox")
        self.notchPlotWidget = self.findChild(QtWidgets.QWidget, "notchPlotWidget")
        self.notchCanvas = MplCanvas(self.notchPlotWidget)
        notchLayout = QtWidgets.QVBoxLayout(self.notchPlotWidget)
        notchLayout.addWidget(self.notchCanvas)

        # ======================================== Bandpass ========================================================= #
        self.bpgroupBox = self.findChild(QtWidgets.QGroupBox, "bpgroupBox")
        self.bpLabel = self.findChild(QtWidgets.QLabel, "bpLabel")
        self.bpCBox = self.findChild(QtWidgets.QCheckBox, "bpCBox")
        self.bpminLabel = self.findChild(QtWidgets.QLabel, "bpminfreqLabel")
        self.minfreqbpBox = self.findChild(QtWidgets.QDoubleSpinBox, "minfreqbpBox")
        self.bpmaxLabel = self.findChild(QtWidgets.QLabel, "bpmaxfreqLabel")
        self.maxfreqbpBox = self.findChild(QtWidgets.QDoubleSpinBox, "maxfreqbpBox")
        self.orderbpLabel = self.findChild(QtWidgets.QLabel, "orderbpLabel")
        self.orderbpBox = self.findChild(QtWidgets.QSpinBox, "orderbpBox")
        self.bandpassPlotWidget = self.findChild(QtWidgets.QWidget, "bandpassPlotWidget")
        self.bandpassCanvas = MplCanvas(self.bandpassPlotWidget)
        bpLayout = QtWidgets.QVBoxLayout(self.bandpassPlotWidget)
        bpLayout.addWidget(self.bandpassCanvas)

        self.defaults = {
            "minfreqnotch": self.minfreqnotchBox.value(),
            "maxfreqnotch": self.maxfreqnotchBox.value(),
            "ordernotch": self.orderNotchBox.value(),
            "minfreqbp": self.minfreqbpBox.value(),
            "maxfreqbp": self.maxfreqbpBox.value(),
            "orderbp": self.orderbpBox.value(),
        }

        # ======================================== CAR ========================================================= #
        self.cargroupBox = self.findChild(QtWidgets.QGroupBox, "cargroupBox")
        self.carLabel = self.findChild(QtWidgets.QLabel, "carLabel")
        self.carCBox = self.findChild(QtWidgets.QCheckBox, "carCBox")

        # Group buttons connection
        self.preprocessingButton.toggled.connect(self.toggle_preprocessing_group)
        self.notchCBox.toggled.connect(self.toggle_notch_controls)
        self.bpCBox.toggled.connect(self.toggle_bandpass_controls)
        self.notchCBox.toggled.connect(self.update_notch_plot)
        self.minfreqnotchBox.valueChanged.connect(self.update_notch_plot)
        self.maxfreqnotchBox.valueChanged.connect(self.update_notch_plot)
        self.orderNotchBox.editingFinished.connect(self.update_notch_plot)
        self.bpCBox.toggled.connect(self.update_bandpass_plot)
        self.minfreqbpBox.valueChanged.connect(self.update_bandpass_plot)
        self.maxfreqbpBox.valueChanged.connect(self.update_bandpass_plot)
        self.orderbpBox.valueChanged.connect(self.update_bandpass_plot)

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
            self.carLabel, self.carCBox, self.notchPlotWidget, self.bandpassPlotWidget, self.bpgroupBox, self.cargroupBox,
            self.notchgroupBox
        ]:
            w.setVisible(False)

        # Resetear los checkboxes para que no estén marcadas
        for box in [self.notchCBox, self.bpCBox, self.carCBox, self.preprocessingButton]: box.setChecked(False)

        # Reseteamos todas las spinboxes para poner sus valores por defecto
        self.minfreqnotchBox.setValue(self.defaults["minfreqnotch"])
        self.maxfreqnotchBox.setValue(self.defaults["maxfreqnotch"])
        self.orderNotchBox.setValue(self.defaults["ordernotch"])
        self.minfreqbpBox.setValue(self.defaults["minfreqbp"])
        self.maxfreqbpBox.setValue(self.defaults["maxfreqbp"])
        self.orderbpBox.setValue(self.defaults["orderbp"])

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
        reply = QMessageBox.question(self, "Delete files", "¿Do you want to delete all the selected files?",
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
        self.selectLabel.setText(f"{count} selected files")

        # Sincronizar con main_window
        self.main_window.selected_files = self.selected_files.copy()
        self.main_window.segmentation_widget.reset_segmentation_state()
        if count > 0:
            self.main_window.nextButton.setDisabled(False)
        else:
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

        # self.main_window.nextButton.setDisabled(False)
        if not self.preprocessingButton.isChecked():
            self.reset_all_controls()
            return

        if self.preprocessingButton.isChecked(): # mostramos los controles de preprocessing (pero siguen ocultos sus parámetros)
            pairs = [
                (self.notchLabel, self.notchCBox),
                (self.bpLabel, self.bpCBox),
                (self.carLabel, self.carCBox),
            ]
            self.cargroupBox.setVisible(True)
            self.bpgroupBox.setVisible(True)
            self.notchgroupBox.setVisible(True)

            for label, checkbox in pairs:
                label.setVisible(True)
                checkbox.setVisible(True)

    def toggle_notch_controls(self, checked):
        '''
                Muestra y oculta los parámetros asociados a 'notch_filyer' cuando se marca o se desmarca su checkbox principal.
                :param checked:
                '''
        if not checked:
            self.minfreqnotchBox.setValue(self.defaults["minfreqnotch"])
            self.maxfreqnotchBox.setValue(self.defaults["maxfreqnotch"])
            self.orderNotchBox.setValue(self.defaults["ordernotch"])
        # self.notchgroupBox.setVisible(checked)
        self.notchPlotWidget.setVisible(checked)
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
        if not checked:
            self.minfreqbpBox.setValue(self.defaults["minfreqbp"])
            self.maxfreqbpBox.setValue(self.defaults["maxfreqbp"])
            self.orderbpBox.setValue(self.defaults["orderbp"])
        # self.bpgroupBox.setVisible(checked)
        self.bandpassPlotWidget.setVisible(checked)
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

        if max_val <= min_val:
            QMessageBox.warning(
                self,
                "Invalid values for bandpass filter.",
                f"For bandpass filtering, <b>max</b> frequency ({max_val}) must be greater than <b>min</b> ({min_val})."
            )

            self.minfreqbpBox.setValue(self.defaults["minfreqbp"])
            self.maxfreqbpBox.setValue(self.defaults["maxfreqbp"])

        self.validating_bandpass = False

    def validate_notch_bounds(self):
        if self.validating_notch:
            return

        self.validating_notch = True

        min_val = self.minfreqnotchBox.value()
        max_val = self.maxfreqnotchBox.value()

        if max_val <= min_val:
            QMessageBox.warning(
                self,
                "Invalid values for notch filter.",
                f"For notch filtering, <b>max</b> frequency ({max_val}) must be greater than <b>min</b> ({min_val})."
            )

            self.minfreqnotchBox.setValue(self.defaults["minfreqnotch"])
            self.maxfreqnotchBox.setValue(self.defaults["maxfreqnotch"])

        self.validating_notch = False

    def update_notch_plot(self):
        if not self.notchCBox.isChecked():
            self.notchCanvas.ax.clear()
            self.notchCanvas.draw()
            return

        fs = 256  # CAMBIAR: Cargar la FS del archivo seleccionado
        low = self.minfreqnotchBox.value()
        high = self.maxfreqnotchBox.value()

        if high <= low or low <= 0 or high >= fs / 2:
            self.notchCanvas.ax.clear()
            self.notchCanvas.ax.set_title("Invalid notch frequency range", fontsize=10, color="#000000")
            self.notchCanvas.draw()
            return

        numtaps = self.orderNotchBox.value()
        b = firwin(numtaps, [low, high], pass_zero=True, fs=fs)
        w, h = freqz(b, worN=1024, fs=fs)

        self.notchCanvas.ax.clear()
        self.notchCanvas.ax.plot(w, 20 * np.log10(np.maximum(abs(h), 1e-6)), color="#ab47bc", linewidth=2.0)
        self.notchCanvas.ax.set_title("Notch Filter", fontsize=10, color="#000000")
        self.notchCanvas.ax.set_ylabel("Gain (dB)", fontsize=9, color="#000000")
        self.notchCanvas.ax.set_xlabel("Frequency (Hz)", fontsize=9, color="#000000")
        self.notchCanvas.ax.set_xlim([0, fs / 2])
        self.notchCanvas.ax.grid(False)
        self.notchCanvas.ax.tick_params(labelsize=8, colors="#000000")
        self.notchCanvas.draw()

    def update_bandpass_plot(self):
        if not self.bpCBox.isChecked():
            self.bandpassCanvas.ax.clear()
            self.bandpassCanvas.draw()
            return

        fs = 256  # CAMBIAR: Cargar la FS del archivo seleccionado
        low = self.minfreqbpBox.value()
        high = self.maxfreqbpBox.value()

        if high <= low or low <= 0 or high >= fs / 2:
            self.bandpassCanvas.ax.clear()
            self.bandpassCanvas.ax.set_title("Invalid bandpass frequency range", fontsize=10, color="#000000")
            self.bandpassCanvas.draw()
            return

        numtaps = self.orderbpBox.value()
        b = firwin(numtaps, [low, high], pass_zero=False, fs=fs)
        w, h = freqz(b, worN=1024, fs=fs)

        self.bandpassCanvas.ax.clear()
        self.bandpassCanvas.ax.plot(w, 20 * np.log10(np.maximum(abs(h), 1e-6)), color="#ec407a", linewidth=2.0)
        self.bandpassCanvas.ax.set_title("Bandpass Filter", fontsize=10, color="#000000")
        self.bandpassCanvas.ax.set_ylabel("Gain (dB)", fontsize=9, color="#000000")
        self.bandpassCanvas.ax.set_xlabel("Frequency (Hz)", fontsize=9, color="#000000")
        self.bandpassCanvas.ax.set_xlim([0, fs / 2])
        self.bandpassCanvas.ax.grid(False)
        self.bandpassCanvas.ax.tick_params(labelsize=8, colors="#000000")
        self.bandpassCanvas.draw()

    def get_preprocessing_config(self):
        config = {
            "selected_files": self.selected_files if self.selected_files else None,
            "apply_preprocessing": True if self.preprocessingButton.isChecked() else None,

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
