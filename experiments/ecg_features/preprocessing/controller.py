from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QScrollArea
from PySide6.QtCore import Qt

class CleanECGHelpDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ECG Cleaning with NeuroKit2")
        self.setMinimumWidth(600)

        # Layout principal
        layout = QVBoxLayout(self)

        # Área de desplazamiento para contenido largo
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # Contenedor del contenido
        content_widget = QLabel(self)
        content_widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        content_widget.setOpenExternalLinks(True)
        scroll_area.setWidget(content_widget)

        # Contenido HTML
        html_content = """
        <h2>ECG Cleaning with NeuroKit2</h2>
        <p><strong>Function:</strong> <code>nk.ecg_clean()</code></p>
        <p>This function cleans an ECG signal to remove noise and improve peak-detection accuracy. Different cleaning methods are implemented.</p>
        <p><strong>Parameters:</strong></p>
        <ul>
            <li><strong>ecg_signal</strong>: The raw ECG signal.</li>
            <li><strong>sampling_rate</strong>: The sampling frequency of the ECG signal (in Hz). Default is 1000.</li>
            <li><strong>method</strong>: The processing pipeline to apply. Can be one of:
                <ul>
                    <li><strong>'neurokit'</strong> (default): 0.5 Hz high-pass Butterworth filter (order = 5), followed by powerline filtering.</li>
                    <li><strong>'biosppy'</strong>: Method used in the BioSPPy package. A FIR filter ([0.67, 45] Hz; order = 1.5 * SR).</li>
                    <li><strong>'pantompkins1985'</strong>: Pan & Tompkins (1985) algorithm for QRS detection.</li>
                    <li><strong>'hamilton2002'</strong>: Hamilton (2002) algorithm for QRS detection.</li>
                    <li><strong>'elgendi2010'</strong>: Elgendi (2010) algorithm for QRS detection.</li>
                    <li><strong>'engzeemod2012'</strong>: EngzeeMod (2012) algorithm for QRS detection.</li>
                </ul>
            </li>
        </ul>
        <p><strong>Returns:</strong> A cleaned ECG signal.</p>
        <p><strong>Example:</strong></p>
        <pre><code>import neurokit2 as nk
ecg = nk.ecg_simulate(duration=10, sampling_rate=1000)
cleaned_ecg = nk.ecg_clean(ecg, sampling_rate=1000, method='neurokit')</code></pre>
        """
        content_widget.setText(html_content)

        # Botón de cierre
        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

class HRVProcessingHelpDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HRV Processing with NeuroKit2")
        self.setMinimumWidth(600)

        # Layout principal
        layout = QVBoxLayout(self)

        # Área de desplazamiento para contenido largo
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # Contenedor del contenido
        content_widget = QLabel(self)
        content_widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        content_widget.setOpenExternalLinks(True)
        scroll_area.setWidget(content_widget)

        # Contenido HTML
        html_content = """
        <h2>HRV Processing with NeuroKit2</h2>
        <p><strong>Function:</strong> <code>nk.ecg_peaks()</code></p>
        <p>This function detects R-peaks in a cleaned ECG signal.</p>
        <p><strong>Parameters:</strong></p>
        <ul>
            <li><strong>ecg_cleaned</strong>: The cleaned ECG signal.</li>
            <li><strong>sampling_rate</strong>: The sampling frequency of the ECG signal (in Hz). Default is 1000.</li>
            <li><strong>method</strong>: The algorithm to be used for R-peak detection. Can be one of:
                <ul>
                    <li><strong>'neurokit'</strong> (default): QRS complexes are detected based on the steepness of the absolute gradient of the ECG signal.</li>
                    <li><strong>'pantompkins1985'</strong>: Pan & Tompkins (1985) algorithm for QRS detection.</li>
                    <li><strong>'hamilton2002'</strong>: Hamilton (2002) algorithm for QRS detection.</li>
                    <li><strong>'elgendi2010'</strong>: Elgendi (2010) algorithm for QRS detection.</li>
                    <li><strong>'engzeemod2012'</strong>: EngzeeMod (2012) algorithm for QRS detection.</li>
                </ul>
            </li>
            <li><strong>correct_artifacts</strong>: Whether to correct artifacts. Default is False.</li>
        </ul>
        <p><strong>Returns:</strong> Detected R-peaks.</p>
        <p><strong>Example:</strong></p>
        <pre><code>import neurokit2 as nk
ecg = nk.ecg_simulate(duration=10, sampling_rate=1000)
cleaned_ecg = nk.ecg_clean(ecg, sampling_rate=1000, method='neurokit')
peaks, _ = nk.ecg_peaks(cleaned_ecg, sampling_rate=1000, method='neurokit', correct_artifacts=True)</code></pre>
        """
        content_widget.setText(html_content)

        # Botón de cierre
        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)


class PreprocessingController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self
        self.first_show = False

        # Connects
        self.view.cleanCBox.toggled.connect(self.on_clean_toggle)
        self.view.hrvCBox.toggled.connect(self.on_hrv_toggle)
        self.view.cleanButton.clicked.connect(self.on_clean_help_button_clicked)
        self.view.hrvprocessButton.clicked.connect(self.on_hrv_help_button_clicked)

    def on_clean_toggle(self, checked):
        """
        This function shows or hides the cleaning controls depending on whether the user chooses to apply them
        or not.
        """
        for widget in [self.view.cleanLabel, self.view.cleanBox, self.view.cleanButton]:
            widget.setVisible(checked)


    def on_hrv_toggle(self, checked):
        """
        This function shows or hides the hrv controls depending on whether the user chooses to apply them
        or not.
        """
        # HRV elements to toggle
        for widget in [self.view.hrvprocessLabel, self.view.hrvprocessBox, self.view.hrvprocessButton]:
            widget.setVisible(checked)
        self.view.hrvLabel.setVisible(not checked)

        # Resample elements to toggle
        for widget in [self.view.resampleLabel, self.view.resampleBox, self.view.resampleLabelAux,
                       self.view.resampleLabelNyquist, self.view.artifactsCBox]:
            widget.setVisible(checked)

    def on_clean_help_button_clicked(self):
        dialog = CleanECGHelpDialog()
        dialog.exec()

    def on_hrv_help_button_clicked(self):
        dialog = HRVProcessingHelpDialog()
        dialog.exec()

