from PySide6 import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
import medusa
import medusa.ecg
from plots_stats.plot_panel.export_dialog import ExportDialog


class PlotController(QtCore.QObject):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.view.controller = self

        self.recording = None # actualizes when loading a valid recording to plot
        self.fs = self.view.main_module.controller.fs
        self.channel_list = self.view.main_module.controller.channel_list
        self.current_window_start = 0  # (s)
        self.window_duration = 5  # (window plot time in (s))
        self.vertical_scale = 1.0  # scale for vertical zoom
        self.total_duration = 0


        self.view.shown.connect(self.on_first_show)
        self.view.sliderRaw.valueChanged.connect(lambda val: self.on_slider_moved("raw", val))
        self.view.sliderClean.valueChanged.connect(lambda val: self.on_slider_moved("clean", val))
        self.view.prevButton.clicked.connect(self.prev_tab)
        self.view.nextButton.clicked.connect(self.next_tab)
        self.view.exportButton.clicked.connect(self.export_figure)
        self.view.updatecleanButton.clicked.connect(lambda: self.update_plot_labels("clean"))
        self.view.updaterawButton.clicked.connect(lambda: self.update_plot_labels("raw"))


    def on_first_show(self):
        """ Load de recording file when the widget is first shown """

        path = self.view.main_module.controller.file_path_to_plot
        try:
            self.recording = medusa.components.Recording.load(path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self.view, "Error", f"Error loading recording:\n{e}")
            return

        self.total_duration = len(self.recording.eeg.times) / self.fs
        self.setup_plot("raw")
        self.setup_plot("clean")

    def setup_plot(self, mode):
        """ Setup the available plots.
        """
        if mode == "raw":
            data = np.array(self.recording.eeg.original_signal)
            placeholder = self.view.plotrawPlaceholder
            slider = self.view.sliderRaw
        else:
            data = np.array(self.recording.eeg.signal)
            placeholder = self.view.plotcleanPlaceholder
            slider = self.view.sliderClean

        # Obtain the time array based on the signal sampling frequency
        n_samples, n_channels = data.shape
        times = self.recording.eeg.times
        if times[-1] > self.total_duration * 1.5:
            times = np.arange(len(times)) / self.fs
        setattr(self, f"{mode}_times", times)

        # Create the figure. Height is adjusted based on the number of channels
        fig_height = max(2.0, n_channels * 0.4)
        fig = Figure(figsize=(8, fig_height))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)

        layout = QtWidgets.QVBoxLayout(placeholder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(canvas)

        setattr(self, f"{mode}_ax", ax)
        setattr(self, f"{mode}_canvas", canvas)
        setattr(self, f"{mode}_data", data)
        setattr(self, f"{mode}_times", times)
        channel_means = np.nanmean(data, axis=0)
        setattr(self, f"{mode}_channel_means", channel_means)

        # Calculate fixed offsets for channels
        spacing = 1.0 / (n_channels + 1)
        offsets = np.linspace(spacing, 1.0 - spacing, n_channels)[::-1]
        setattr(self, f"{mode}_channel_offsets", offsets)

        # Calculate adaptative initial scale using the 95 percentile of the amplitude of each channel
        amp_ref = np.nanmedian([np.nanpercentile(np.abs(data[:, ch] - channel_means[ch]), 95) for ch in range(n_channels)])
        if amp_ref == 0 or np.isnan(amp_ref):
            amp_ref = 1e-6  # avoid zero division
        self.vertical_scale = (0.6 * spacing) / amp_ref
        self.vertical_scale = np.clip(self.vertical_scale, 1e-3, 0.1)
        setattr(self, f"{mode}_base_scale", self.vertical_scale)
        setattr(self, f"{mode}_scale", self.vertical_scale)

        # Configure slider
        max_start = max(0, self.total_duration - self.window_duration)
        slider.setMinimum(0)
        slider.setMaximum(int(max_start))
        slider.setSingleStep(1)
        slider.setPageStep(int(self.window_duration))
        slider.setValue(0)

        canvas.mpl_connect("scroll_event", lambda event, m=mode: self.on_scroll(event, m))

        self.draw_window(mode)
        self.update_plot_labels(mode)


    def draw_window(self, mode):
        ax = getattr(self, f"{mode}_ax")
        canvas = getattr(self, f"{mode}_canvas")
        data = getattr(self, f"{mode}_data")
        times = getattr(self, f"{mode}_times")
        offsets = getattr(self, f"{mode}_channel_offsets")
        channel_means = getattr(self, f"{mode}_channel_means")

        start_idx = int(self.current_window_start * self.fs)
        end_idx = int((self.current_window_start + self.window_duration) * self.fs)
        end_idx = min(end_idx, len(times))

        segment = data[start_idx:end_idx, :]
        segment_times = times[start_idx:end_idx]

        ax.cla()

        n_channels = segment.shape[1]
        cmap = plt.cm.get_cmap("tab10", n_channels)
        colors = [cmap(i) for i in range(n_channels)]

        scale = getattr(self, f"{mode}_scale", getattr(self, f"{mode}_base_scale", 1.0))
        for ch in range(n_channels):
            centered = segment[:, ch] - channel_means[ch]
            amplified = centered * scale
            ax.plot(segment_times, amplified + offsets[ch], lw=0.8, color=colors[ch])

        # Set titles based on the editable params
        title_edit = getattr(self.view, f"title{mode}")
        xlabel_edit = getattr(self.view, f"x{mode}")
        ylabel_edit = getattr(self.view, f"y{mode}")
        title_text = title_edit.text() if title_edit.text().strip() else f"EEG {'RAW' if mode == 'raw' else 'CLEAN'} Signal"
        xlabel_text = xlabel_edit.text() if xlabel_edit.text().strip() else "Time (s)"
        ylabel_text = ylabel_edit.text() if ylabel_edit.text().strip() else "Channels"

        ax.set_ylim(0, 1)
        ax.set_xlim(segment_times[0], segment_times[-1])
        ax.set_xlabel(xlabel_text)
        ax.set_ylabel(ylabel_text)
        ax.set_yticks(offsets)
        ax.set_yticklabels(self.channel_list)
        ax.invert_yaxis()
        ax.set_title(title_text)

        canvas.draw_idle()

    def update_plot_labels(self, mode):
        """Actualizes title and axis labels with QLineEdit information."""
        ax = getattr(self, f"{mode}_ax", None)
        canvas = getattr(self, f"{mode}_canvas", None)

        title_edit = getattr(self.view, f"title{mode}")
        xlabel_edit = getattr(self.view, f"x{mode}")
        ylabel_edit = getattr(self.view, f"y{mode}")

        ax.set_title(title_edit.text() or f"EEG {'raw' if mode == 'raw' else 'clean'} Signal")
        ax.set_xlabel(xlabel_edit.text() or "Time (s)")
        ax.set_ylabel(ylabel_edit.text() or "Channels")

        canvas.draw_idle()


    def on_scroll(self, event, mode):
        """Zoom signal amplitude"""

        zoom_factor = 1.2
        scale = getattr(self, f"{mode}_scale", getattr(self, f"{mode}_base_scale", 1.0))
        base_scale = getattr(self, f"{mode}_base_scale", 1.0)

        if event.button == 'up':
            scale *= zoom_factor
        elif event.button == 'down':
            scale /= zoom_factor

        # Limit the base_scale
        min_scale = base_scale * 0.1
        max_scale = base_scale * 10.0
        scale = np.clip(scale, min_scale, max_scale)
        setattr(self, f"{mode}_scale", scale)

        self.draw_window(mode)

    def on_slider_moved(self, mode, value):
        """Actualizes temporal position depending on slider"""

        self.current_window_start = float(value)
        self.draw_window(mode)


    def prev_tab(self):
        """Go back to the previous tab."""
        current = self.view.tabWidget.currentIndex()
        if current > 0:
            self.view.tabWidget.setCurrentIndex(current - 1)

    def next_tab(self):
        """Go forward to the next tab."""
        current = self.view.tabWidget.currentIndex()
        if current < self.view.tabWidget.count() - 1:
            self.view.tabWidget.setCurrentIndex(current + 1)

    def export_figure(self, tab):
        """Export the figure from the given tab. Open a QFileDialog to choose the path and a dialog
        with saving options."""

        current_index = self.view.tabWidget.currentIndex()
        mode = "raw" if current_index == 0 else "clean"
        canvas = getattr(self, f"{mode}_canvas", None)
        if canvas is None:
            QtWidgets.QMessageBox.warning(self.view, "Export", "No hay figura para exportar.")
            return

        fig = canvas.figure

        dlg = ExportDialog(self.view)
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return
        vals = dlg.get_values()
        fmt = vals["format"]
        dpi = vals["dpi"]
        width_px = vals["width"]
        height_px = vals["height"]
        transparent = vals["transparent"]
        bg_color = vals["bg_color"]

        suggested_name = f"EEG_{mode}.{fmt}"
        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self.view, "Save image", suggested_name,
                                              f"{fmt.upper()} (*.{fmt})")
        if not fname:
            return

        # Asjust figure size: matplotlib uses inches so we have to convert px to inches
        inches_width = width_px / dpi
        inches_height = height_px / dpi

        original_size = fig.get_size_inches()
        try:
            fig.set_size_inches(inches_width, inches_height)

            # Si no es transparente, usar el color de fondo elegido
            facecolor = "none" if transparent else bg_color
            fig.savefig(fname, dpi=dpi, transparent=transparent,
                        bbox_inches="tight", facecolor=facecolor)
        finally:
            # restore original sizer for avoid afecting the canvas visual representation in the widget
            fig.set_size_inches(original_size)

        QtWidgets.QMessageBox.information(self.view, "Export", f"Saved to:\n{fname}")
