import numpy as np
from PySide6 import QtWidgets
from scipy.signal import firwin, freqz
from ecg_features.preprocessing.flow import reset_all_controls

class PreprocessingController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self
        self.first_show = False

        # Connects
        self.view.cleanCBox.toggled.connect(self.on_clean_toggle)
        self.view.hrvCBox.toggled.connect(self.on_hrv_toggle)
        self.view.resampleCBox.toggled.connect(self.on_resample_toggle)

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
        for widget in [self.view.resampleCBox, self.view.resampleLabel]:
            widget.setVisible(checked)
        self.view.resampleCBox.setChecked(False)

    def on_resample_toggle(self, checked):
        """
        Show or hide resampling controls based on the checkbox state. Resets resample frequency spinbox when disabled.
        """

        for w in [self.view.resampleLabelAux, self.view.resampleBox, self.view.resampleLabelNyquist]:
            w.setVisible(checked)
        self.view.resampleLabel.setVisible(not checked)

        if not checked:
            # Reset defaults
            self.view.resampleBox.setValue(self.view.defaults["resamplefs"])

