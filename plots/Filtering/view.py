from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import os
import medusa.components
import numpy as np

class MplCanvas(FigureCanvas):
    """
        Canvas class for the filter canvas
    """
    def __init__(self, parent=None, width=4, height=3, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

# Load UI class
ui_filtering_plot = loadUiType('plots/filtering/view.ui')[0]

class FilteringPlotWidget(QtWidgets.QWidget, ui_filtering_plot):

    def __init__(self, main_window):
        super().__init__()
        self.setupUi(self)
        self.main_window = main_window

        self.selectfileButton.clicked.connect(self.on_select_file_click)

        self.channelsLabel.setVisible(False)
        self.channelsBox.setVisible(False)
        self.windowLabel.setVisible(False)
        self.windowBox.setVisible(False)

        # --- Signal plots setup ---
        self.originalsignalCanvas = MplCanvas(self.originalPlotWidget)
        originalLayout = QtWidgets.QVBoxLayout(self.originalPlotWidget)
        originalLayout.addWidget(self.originalsignalCanvas)

        self.filteredsignalCanvas = MplCanvas(self.filteredPlotWidget)
        filteredLayout = QtWidgets.QVBoxLayout(self.filteredPlotWidget)
        filteredLayout.addWidget(self.filteredsignalCanvas)

        # Data placeholders
        self.original_signal = None
        self.filtered_signal = None
        self.fs = None

        # Conectar cambios en la UI
        self.channelsBox.currentIndexChanged.connect(self.update_plots)
        self.windowBox.valueChanged.connect(self.update_plots)

    def on_select_file_click(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,  # parent
            "Select file .mat",
            os.getcwd(),
            "File MAT (*.mat)"
        )

        if file_path:
            self.selectedLabel.setText(file_path)

            self.channelsLabel.setVisible(True)
            self.channelsBox.setVisible(True)
            self.windowLabel.setVisible(True)
            self.windowBox.setVisible(True)

            data = medusa.components.Recording.load_from_mat(file_path)
            self.original_signal = data.eeg.original_signal   # shape: (samples, channels)
            self.filtered_signal = data.eeg.signal            # shape: (samples, channels)
            times = data.eeg.times                            # in samples
            self.fs = data.eeg.fs
            channel_names = data.eeg.channel_set.l_cha

            # Adjust window time
            duration_seconds = len(times) / self.fs
            self.windowBox.setMinimum(1)
            self.windowBox.setMaximum(int(duration_seconds))

            # Fill combobox with channel names
            self.channelsBox.clear()
            self.channelsBox.addItems([str(ch) for ch in channel_names])
            self.channelsBox.setCurrentIndex(0)

            self.update_plots()

        else:
            self.channelsLabel.setVisible(False)
            self.channelsBox.setVisible(False)
            self.windowLabel.setVisible(False)
            self.windowBox.setVisible(False)

    def update_plots(self):
        """Draw the signals of the selected channels in the time interval especified"""
        if self.original_signal is None or self.filtered_signal is None:
            return

        channel_idx = self.channelsBox.currentIndex()
        window_sec = self.windowBox.value()

        # Convertir ventana de segundos a muestras
        n_samples = int(window_sec * self.fs)
        sig_original = self.original_signal[:n_samples, channel_idx]
        sig_filtered = self.filtered_signal[:n_samples, channel_idx]

        # Crear vector de tiempo en segundos
        times = (1 / self.fs) * np.arange(n_samples)

        # --- Plot original signal ---
        self.originalsignalCanvas.ax.clear()
        self.originalsignalCanvas.ax.plot(times, sig_original, color="tab:blue")
        self.originalsignalCanvas.ax.set_title(f"Original signal - Channel {channel_idx}")
        self.originalsignalCanvas.ax.set_xlabel("Time [s]")
        self.originalsignalCanvas.ax.set_ylabel("Amplitud")
        self.originalsignalCanvas.draw()

        # --- Plot filtered signal ---
        self.filteredsignalCanvas.ax.clear()
        self.filteredsignalCanvas.ax.plot(times, sig_filtered, color="tab:orange")
        self.filteredsignalCanvas.ax.set_title(f"Filtered signal - Channel {channel_idx}")
        self.filteredsignalCanvas.ax.set_xlabel("Time [s]")
        self.filteredsignalCanvas.ax.set_ylabel("Amplitud")
        self.filteredsignalCanvas.draw()
