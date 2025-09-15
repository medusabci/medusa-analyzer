from PySide6 import QtWidgets, QtGui, QtCore
from eeg_features.bands_table import BandTableWidget

class ParametersController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self

        self.selected_bands_by_type = {"rp": []}
        self.rp_band_editor = None

        # Relative power
        self.view.rpCBox.toggled.connect(self.on_rpCBox_toggled)
        self.view.rpButton.clicked.connect(lambda: self.on_bandTableButton_clicked("rp"))

        # STATISTICS AND NONLINEAR - Element setup
        self.view.msampenCBox.toggled.connect(self.on_msampenCBox_toggled)
        self.view.sampenCBox.toggled.connect(self.on_sampenCBox_toggled)
        self.view.ctmCBox.toggled.connect(self.on_ctmCBox_toggled)
        self.view.psdCBox.toggled.connect(self.on_psdCBox_toggled)
        self.view.mlzcCBox.toggled.connect(self.on_mlzcCBox_toggled)

        # CONNECTIVITY - Element setup
        self.view.aecCBox.toggled.connect(self.on_aecCBox_toggled)
        self.view.iacCBox.toggled.connect(self.on_iacCBox_toggled)

    # PSD RP AP MF SE
    def on_psdCBox_toggled(self):
        """
        Triggered when the PSD checkbox is toggled.
        Manages the visibility of the PSD config parameters.
        """
        visible = self.view.psdCBox.isChecked()
        for widget in [self.view.segmentpsdLabel, self.view.segmentpsdBox, self.view.overlappsdLabel, self.view.overlappsdBox,
                       self.view.psdcomboBox, self.view.windowpsdLabel]:
            widget.setVisible(visible)
        self.view.segmentpsdBox.setValue(self.view.defaults["psdsegment"])
        self.view.overlappsdBox.setValue(self.view.defaults["psdoverlap"])
        self.view.psdcomboBox.setCurrentIndex(6)

    def on_rpCBox_toggled(self):
        """
        Triggered when the relative power checkbox is toggled.
        Manages the visibility of the RP config parameters.
        """
        visible = self.view.rpCBox.isChecked()

        self.view.rpselectedbandsLabel.setVisible(visible)
        self.view.rpselectedbandsauxLabel.setVisible(visible)
        self.view.rpLabel.setVisible(visible)

        if not self.view.main_window.controller.preproc_config['band_segmentation']:
            self.view.rpButton.setVisible(visible)
            if visible:
                QtWidgets.QMessageBox.warning(
                    self.view,
                    "Relative Power",
                    "We are currently working only with the broadband signal, since no band filtering "
                    "has been applied during preprocessing.\n\n"
                    "Please use the 'Edit bands' button to define at least one additional frequency band "
                    "in order to enable the calculation of relative power for that band."
                )

        if not visible:
            self.view.rpLabel.setText("None")
            self.rp_band_editor = None
            self.selected_bands_by_type["rp"] = []

    def on_ctmCBox_toggled(self):
        """
        Triggered when the CTM checkbox is toggled.
        Manages the visibility of the CTM config parameters.
        """
        visible = self.view.ctmCBox.isChecked()
        for widget in [self.view.ctmrLabel, self.view.ctmrBox]:
            widget.setVisible(visible)
        self.view.ctmrBox.setValue(self.view.defaults["ctmradius"])

    def on_sampenCBox_toggled(self):
        """
        Triggered when the SampEn checkbox is toggled.
        Manages the visibility of the SampEn config parameters.
        """
        visible = self.view.sampenCBox.isChecked()
        for widget in [self.view.sampenmLabel, self.view.sampenmBox, self.view.sampenrLabel, self.view.sampenrBox]:
            widget.setVisible(visible)
        self.view.sampenmBox.setValue(self.view.defaults["sampm"])
        self.view.sampenrBox.setValue(self.view.defaults["sampradius"])

    def on_msampenCBox_toggled(self):
        """
        Triggered when the Multiscale SampEn checkbox is toggled.
        Manages the visibility of the Multiscale SampEn config parameters.
        """
        visible = self.view.msampenCBox.isChecked()
        for widget in [self.view.maxscaleLabel, self.view.msampenscaleBox, self.view.msampenmLabel, self.view.msampenmBox,
                       self.view.msampenrLabel, self.view.msampenrBox]:
            widget.setVisible(visible)
        self.view.msampenscaleBox.setValue(self.view.defaults["multisampmaxscale"])
        self.view.msampenmBox.setValue(self.view.defaults["multisampm"])
        self.view.msampenrBox.setValue(self.view.defaults["multisampradius"])

    def on_mlzcCBox_toggled(self):
        """
        Triggered when the Multiscale LZC checkbox is toggled.
        Manages the visibility of the Multiscale LZC config parameters.
        """
        visible = self.view.mlzcCBox.isChecked()
        for widget in [self.view.mlzcscalesLabel, self.view.mlzcEdit]:
            widget.setVisible(visible)
        self.view.mlzcEdit.setText('[1, 3, 5]')

    def on_iacCBox_toggled(self):
        """
        Triggered when the IAC checkbox is toggled.
        Manages the visibility of the IAC config parameters.
        """
        visible = self.view.iacCBox.isChecked()
        if visible:
            self.view.iacortButton.setChecked(True)
        else:
            self.view.iacortButton.setChecked(False)
        for widget in [self.view.iacortLabel, self.view.iacortButton]:
            widget.setVisible(visible)

    def on_aecCBox_toggled(self):
        """
        Triggered when the AEC checkbox is toggled.
        Manages the visibility of the AEC config parameters.
        """
        visible = self.view.aecCBox.isChecked()
        if visible:
            self.view.aecortButton.setChecked(True)
        else:
            self.view.aecortButton.setChecked(False)
        for widget in [self.view.aecortLabel, self.view.aecortButton]:
            widget.setVisible(visible)

    def on_bandTableButton_clicked(self, band_type):
        """
        Triggered when the 'Edit bands' button is clicked.
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
        self.rp_band_editor.show()

    def update_band_label(self, filtering_target, bands):
        """
        Updates the labels with the names of the selected bands
        """
        self.view.selected_bands_by_type = getattr(self, "selected_bands_by_type", {})
        self.view.selected_bands_by_type[filtering_target] = bands

        if bands:
            names = [f"{b['name']} ({b['min']}–{b['max']} Hz)" for b in bands]
            self.view.rpLabel.setText(", ".join(names))
        else:
            self.view.rpLabel.setText("None")