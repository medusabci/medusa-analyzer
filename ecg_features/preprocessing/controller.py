import numpy as np
from PySide6 import QtWidgets
from scipy.signal import firwin, freqz
from ecg_features.preprocessing.flow import reset_all_controls

class PreprocessingController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self
        self.first_show = False

        # # Data preprocessing
        self.view.preprocessingButton.toggled.connect(self.on_preprocessing_toggle)
        # # Baseline
        self.view.baselineCBox.toggled.connect(self.on_baseline_toggle)
        # self.view.notchCBox.toggled.connect(lambda: self.update_filter_plot('notch'))
        # self.view.drawnotchButton.clicked.connect(lambda: self.update_filter_plot('notch'))
        # bg_color = self.view.palette().color(self.view.backgroundRole()).name()
        # self.view.notchCanvas.fig.patch.set_facecolor(bg_color)
        # self.view.notchCanvas.ax.set_facecolor(bg_color)
        # self.view.minfreqnotchBox.editingFinished.connect(lambda: self.validate_filter_bounds("notch"))
        # self.view.maxfreqnotchBox.editingFinished.connect(lambda: self.validate_filter_bounds("notch"))
        # # Bandpass
        # self.view.bpCBox.toggled.connect(self.on_bandpass_toggle)
        # self.view.bpCBox.toggled.connect(lambda: self.update_filter_plot('bandpass'))
        # self.view.drawbpButton.clicked.connect(lambda: self.update_filter_plot('bandpass'))
        # self.view.bandpassCanvas.fig.patch.set_facecolor(bg_color)
        # self.view.bandpassCanvas.ax.set_facecolor(bg_color)
        # self.view.minfreqbpBox.editingFinished.connect(lambda: self.validate_filter_bounds("bandpass"))
        # self.view.maxfreqbpBox.editingFinished.connect(lambda: self.validate_filter_bounds("bandpass"))
        # self.view.minfreqbpBox.valueChanged.connect(lambda: self.view.minbroadBox.setValue(self.view.minfreqbpBox.value()))
        # self.view.maxfreqbpBox.valueChanged.connect(lambda: self.view.maxbroadBox.setValue(self.view.maxfreqbpBox.value()))

        #
        # # Band segmentation
        # self.view.bandCBox.toggled.connect(self.on_band_filtering_toggle)
        # self.view.bandButton.clicked.connect(self.open_band_editor)
        # # self.selected_bands = []
        # self.band_editor = None
        #
        # # Set initial state
        # self.view.shown.connect(self.on_show_event)
        # reset_all_controls(self)

    def on_preprocessing_toggle(self, checked):
        """
        This function shows or hides the preprocessing controls depending on whether the user chooses to apply them
        or not.
        """
        if not checked:
            reset_all_controls(self)
            return
        else: # Show all the checkboxes, but keep their parameters hidden
            elements = [
                self.view.baselineLabel, self.view.baselineCBox, self.view.baselinegroupBox,
                self.view.bpLabel, self.view.bpCBox, self.view.bpgroupBox,
                self.view.normLabel, self.view.normCBox, self.view.normgroupBox,
            ]
            for elm in elements:
                elm.setVisible(True)

    def on_notch_toggle(self, checked):
        """
        Shows (or hides) the parameters associated with 'notch_filter' when its main checkbox is checked (or
        unchecked).
        """

        # Show (or hide)
        self.view.baselinePlotWidget.setVisible(checked)
        self.view.baselineLabel.setVisible(checked)
        self.view.minfreqbaselineBox.setVisible(checked)
        self.view.orderbaselineLabel.setVisible(checked)
        self.view.orderbaselineBox.setVisible(checked)
        self.view.drawabaselineButton.setVisible(checked)
        self.view.winbaselineBox.setVisible(checked)
        self.view.winbaselineLabel.setVisible(checked)

        # Reset default values
        if not checked:
            self.view.minfreqnotchBox.setValue(self.view.defaults["minfreqnotch"])
            self.view.orderNotchBox.setValue(self.view.defaults["ordernotch"])
            self.view.winnotchBox.setCurrentIndex(9) # Hamming