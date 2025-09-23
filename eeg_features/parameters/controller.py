from PySide6 import QtWidgets
from eeg_features.bands_table import BandTableWidget

class ParametersController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self

        # Variables
        self.selected_bands_by_type = {"rp": []}
        self.rp_band_editor = None

        # Relative power
        self.view.rpCBox.toggled.connect(self.on_rp_toggled)
        self.view.rpButton.clicked.connect(lambda: self.on_bandTable_clicked("rp"))

        # STATISTICS AND NONLINEAR - Element setup
        self.view.psdCBox.toggled.connect(self.on_psd_toggled)
        self.view.sampenCBox.toggled.connect(self.on_sampen_toggled)
        self.view.msampenCBox.toggled.connect(self.on_msampen_toggled)
        self.view.ctmCBox.toggled.connect(self.on_ctm_toggled)
        self.view.mlzcCBox.toggled.connect(self.on_mlzc_toggled)

        # CONNECTIVITY - Element setup
        self.view.aecCBox.toggled.connect(self.on_aec_toggled)
        self.view.iacCBox.toggled.connect(self.on_iac_toggled)


    def on_rp_toggled(self):
        """
        Manages the visibility of the RP config parameters.
        """
        visible = self.view.rpCBox.isChecked()

        # Visibility of the labels
        self.view.rpLabel.setVisible(visible)
        self.view.rpselectedbandsLabel.setVisible(visible)
        self.view.rpselectedbandsauxLabel.setVisible(visible)

        # If no band segmentation has been applied, show a warning when enabling RP and activate the button to select
        # the bands
        if not self.view.main_window.controller.preproc_config['band_segmentation']:
            self.view.rpButton.setVisible(visible) # Activate the button to select the bands
            # Show a warning only if the checkbox has been activated
            if visible:
                QtWidgets.QMessageBox.warning(
                    self.view,
                    "Relative Power",
                    "We are currently working only with the broadband signal, since no band filtering "
                    "has been applied during preprocessing.\n\n"
                    "Please use the 'Edit bands' button to define at least one additional frequency band "
                    "in order to enable the calculation of relative power for that band."
                )

        # # if unchecked, reset the label and the selected bands
        # if not visible:
        #     self.view.rpLabel.setText("None")
        #     self.rp_band_editor = None
        #     self.selected_bands_by_type["rp"] = []

    def on_bandTable_clicked(self, band_type):
        """
        Opens the band table dialog for relative power band selection.
        """
        # If it is not initialized, do it
        if self.rp_band_editor is None:
            idx = self.view.main_window.stackedWidget.currentIndex()
            self.rp_band_editor = BandTableWidget(
                preprocessing_widget= self.view.main_window.stackedWidget.widget(idx-2).controller,
                parameters_widget=self,
                band_type='rp'
            )
            self.rp_band_editor.setModal(True)  # Disables the MainWindow without closing or breaking inheritance.
            self.rp_band_editor.show()
        # Otherwise, just show it
        self.rp_band_editor.show()


    def update_band_label(self, filtering_target, bands):
        """
        Updates the labels with the names of the selected bands
        """
        self.view.selected_bands_by_type = getattr(self, "selected_bands_by_type", {})
        self.view.selected_bands_by_type[filtering_target] = bands

        # Edit the label with the names and ranges of the selected bands, or "None" if no band is selected
        if bands:
            names = [f"{b['name']} ({b['min']}–{b['max']} Hz)" for b in bands]
            self.view.rpLabel.setText(", ".join(names))
        else:
            self.view.rpLabel.setText("None")


    def on_psd_toggled(self):
        """
        Manages the visibility of the PSD config parameters.
        """
        # Visibility of the elements
        visible = self.view.psdCBox.isChecked()
        for widget in [self.view.segmentpsdLabel, self.view.segmentpsdBox, self.view.overlappsdLabel, self.view.overlappsdBox,
                       self.view.psdcomboBox, self.view.windowpsdLabel]:
            widget.setVisible(visible)
        # Default values
        self.view.segmentpsdBox.setValue(self.view.defaults["psdsegment"])
        self.view.overlappsdBox.setValue(self.view.defaults["psdoverlap"])
        self.view.psdcomboBox.setCurrentIndex(6) # Default window


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

    def on_msampen_toggled(self):
        """
        Manages the visibility of the Multiscale SampEn config parameters.
        """
        # Visibility of the elements
        visible = self.view.msampenCBox.isChecked()
        for widget in [self.view.maxscaleLabel, self.view.msampenscaleBox, self.view.msampenmLabel, self.view.msampenmBox,
                       self.view.msampenrLabel, self.view.msampenrBox]:
            widget.setVisible(visible)
        # Default values
        self.view.msampenscaleBox.setValue(self.view.defaults["multisampmaxscale"])
        self.view.msampenmBox.setValue(self.view.defaults["multisampm"])
        self.view.msampenrBox.setValue(self.view.defaults["multisampradius"])


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


    def on_mlzc_toggled(self):
        """
        Manages the visibility of the Multiscale LZC config parameters.
        """
        # Visibility of the elements
        visible = self.view.mlzcCBox.isChecked()
        for widget in [self.view.mlzcscalesLabel, self.view.mlzcEdit]:
            widget.setVisible(visible)
        # Default values
        self.view.mlzcEdit.setText('[1, 3, 5]')


    def on_aec_toggled(self):
        """
        Manages the visibility of the AEC config parameters.
        """
        # Visibility of the elements
        visible = self.view.aecCBox.isChecked()
        for widget in [self.view.aecortLabel, self.view.aecortButton]:
            widget.setVisible(visible)
        # Default values
        self.view.aecortButton.setChecked(visible)


    def on_iac_toggled(self):
        """
        Manages the visibility of the IAC config parameters.
        """
        visible = self.view.iacCBox.isChecked()
        for widget in [self.view.iacortLabel, self.view.iacortButton]:
            widget.setVisible(visible)
        # Default values
        self.view.iacortButton.setChecked(visible)
