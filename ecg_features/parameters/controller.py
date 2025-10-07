from PySide6 import QtWidgets
from ecg_features.parameters.bands_table import BandTableWidget

class ParametersController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self

        # Variables
        self.selected_bands = {}
        self.band_editor = None

        # Relative power
        self.view.bandButton.clicked.connect(lambda: self.on_bandTable_clicked())

        # Element setup
        self.view.sampenCBox.toggled.connect(self.on_sampen_toggled)
        self.view.ctmCBox.toggled.connect(self.on_ctm_toggled)
        self.view.dfaCBox.toggled.connect(self.on_dfa_toggled)

    def on_bandTable_clicked(self):
        """
        Opens the band table dialog for band selection.
        """
        # If it is not initialized, do it
        if self.band_editor is None:
            idx = self.view.main_window.stackedWidget.currentIndex()
            self.band_editor = BandTableWidget(
                parameters_widget=self,
            )
            self.band_editor.setModal(True)  # Disables the MainWindow without closing or breaking inheritance.
            self.band_editor.show()
        # Otherwise, just show it
        self.band_editor.show()


    def update_band_label(self, bands):
        """
        Updates the labels with the names of the selected bands
        """
        self.selected_bands = bands

        # Edit the label with the names and ranges of the selected bands, or "None" if no band is selected
        if bands:
            names = [f"{b['name']} ({b['min']}–{b['max']} Hz)" for b in bands]
            self.view.bandLabel.setText(", ".join(names))
        else:
            self.view.bandLabel.setText("None")


    def on_sampen_toggled(self):
        """
        Manages the visibility of the SampEn config parameters.
        """
        # Visibility of the elements
        visible = self.view.sampenCBox.isChecked()
        for widget in [self.view.sampenmLabel, self.view.sampenmBox, self.view.sampenrLabel, self.view.sampenrBox]:
            widget.setVisible(visible)
        # Default values
        self.view.sampenmBox.setValue(self.view.defaults["sampm"])
        self.view.sampenrBox.setValue(self.view.defaults["sampradius"])


    def on_ctm_toggled(self):
        """
        Manages the visibility of the CTM config parameters.
        """
        # Visibility of the elements
        visible = self.view.ctmCBox.isChecked()
        for widget in [self.view.ctmrLabel, self.view.ctmrBox]:
            widget.setVisible(visible)
        # Default values
        self.view.ctmrBox.setValue(self.view.defaults["ctmradius"])

    def on_dfa_toggled(self):
        """
        Manages the visibility of the DFA config parameters.
        """
        # Visibility of the elements
        visible = self.view.dfaCBox.isChecked()
        for widget in [self.view.dfanLabel, self.view.dfanBox, self.view.dfabLabel, self.view.dfabBox]:
            widget.setVisible(visible)
        # Default values
        self.view.dfanBox.setValue(self.view.defaults["dfan"])
        self.view.dfabBox.setValue(self.view.defaults["dfab"])

