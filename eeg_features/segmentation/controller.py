from PySide6 import QtWidgets
from PySide6.QtCore import QStringListModel
import marks_utils
from scipy.stats import norm


class SegmentationController:
    def __init__(self, ui):
        self.view = ui

        # Conditions/Events
        self.view.conditionRButton.clicked.connect(self.on_segmentation_toggle)
        self.view.eventRButton.clicked.connect(self.on_segmentation_toggle)
        self.view.trialBox.editingFinished.connect(self.update_max_samples)
        self.view.winBox_1.editingFinished.connect(self.update_max_samples)
        self.view.winBox_2.editingFinished.connect(self.update_max_samples)

        # Normalization
        self.view.normCBox.toggled.connect(self.on_normalization_click)
        # Thresholding
        self.view.thresCBox.toggled.connect(self.on_threshold_click)
        self.view.threshelpButton.clicked.connect(self.show_threshold_help)
        self.view.threskBox.valueChanged.connect(self._set_sigma_percent)
        # Resample
        self.view.resampleCBox.toggled.connect(self.on_resample_click)


    def on_segmentation_toggle(self):
        """
        Handle toggling to 'condition' or 'event' segmentation mode.
        """
        # Condition
        if self.view.conditionRButton.isChecked():
            self.view.normLabel.setText('- Over condition segment')
            self.view.averageLabel.setText('- Average all the epochs of each condition')
            self._event_element_visibility(False)
            self._condition_element_visibility(True)
        # Event
        if self.view.eventRButton.isChecked():
            self.view.normLabel.setText('- Over event window')
            self.view.averageLabel.setText('- Average all the epochs of each event')
            self._event_element_visibility(True)
            self._condition_element_visibility(False)

        self._reset_segmentation_params()
        self.on_normalization_click(self.view.normCBox.isChecked())
        self.update_next_button_state()
    # Helpers to show/hide event/condition elements
    def _event_element_visibility(self, enabled: bool):
        for w in [self.view.winLabel_1, self.view.winBox_1, self.view.winLabel_2, self.view.winBox_2]:
            w.setVisible(enabled)
    def _condition_element_visibility(self, enabled: bool):
        for w in [self.view.trialLabel, self.view.trialBox, self.view.trialstrideLabel, self.view.trialstrideBox]:
            w.setVisible(enabled)
    # Helper to reset the boxes values to default
    def _reset_segmentation_params(self):
        self.view.trialBox.setValue(self.defaults["triallength"])
        self.view.trialstrideBox.setValue(self.defaults["trialstride"])
        self.view.winBox_1.setValue(self.defaults["windowbox1"])
        self.view.winBox_2.setValue(self.defaults["windowbox2"])


    def on_threshold_click(self, checked):
        """
        Show or hide threshold-related controls based on the checkbox state.
        Resets spinboxes to default values when disabled.
        """
        # Update the maximum number of samples
        self.update_max_samples()

        for w in [self.view.threskLabel, self.view.threskBox, self.view.threskLabelaux, self.view.thressampLabel,
                  self.view.thressampBox, self.view.threschanLabel, self.view.threschanBox, self.view.threshelButton]:
            w.setVisible(checked)
        self.view.thresLabel.setVisible(not checked)
        # If deactivated, reset values to default
        if not checked:
            self.view.threskBox.setValue(self.defaults["threshold"])
            self.view.thressampBox.setValue(self.defaults["thressamples"])
            self.view.threschanBox.setValue(self.defaults["threschannels"])
    # Helper function to estimate the percentile based on the sigma value
    def _set_sigma_percent(self):
        percent = norm.cdf(self.view.threskBox.value()) - norm.cdf(-self.view.threskBox.value())
        percent *= 100
        self.view.threskLabelaux.setText(f"Percentile:{percent:.2f}%")


    def show_threshold_help(self):
        """
        Show or hide threshold-related help text.
        """
        QtWidgets.QMessageBox.information(
            self,
            "Help - Thresholding",
            """
            <html>
            <head><style>p { text-align: justify; }</style></head>
            <body>
            <p>This preprocessing step <b>discards epochs</b> exceeding a statistical threshold based on samples and channels.</p>
            <p><b>Statistical Thresholding:</b><br><br>
               &bull; <b>k</b>: Std deviation multiplier for threshold calculation.<br>
               &bull; <b>Samples</b>: Minimum samples exceeding threshold to discard an epoch.<br>
               &bull; <b>Channels</b>: Minimum channels exceeding sample threshold.</p>
            </body>
            </html>
            """
        )


    def update_max_samples(self):
        """
        Update the maximum allowable samples for thresholding based on segmentation mode and parameters.
        """
        if self.view.conditionRButton.isChecked():
            max_samples = (self.view.trialBox.value()/1000) * self.view.main_window.sampling_frequency
        else:
            max_samples = -self.view.winBox_1.value() + self.view.winBox_2.value()
            max_samples = (max_samples/1000) * self.view.main_window.sampling_frequency

        self.view.thressampBox.setMaximum(int(max_samples))


    def on_normalization_click(self, checked):
        """
        Show or hide normalization controls based on the checkbox state and segmentation mode.
        Resets baseline spinboxes and radio buttons when normalization is disabled.
        """
        # Element visibility
        for w in (self.view.zscoreRButton, self.view.dcRButton):
            w.setVisible(checked)
        self.view.normLabel.setVisible(not checked)
        # Only in event mode, show baseline elements
        for w in (self.view.baselineLabel_1, self.view.baselineLabel_2,
                  self.view.baselineCBox_1, self.view.baselineCBox_2):
            w.setVisible(checked and self.view.eventRButton.isChecked())

        # Reset default values
        if checked and self.view.conditionRButton.isChecked():
            self._reset_baseline_elements()

        # Reset default values
        if not checked:
            self._reset_baseline_elements()
            # Disable both radiobuttons
            for rb in (self.view.zscoreRButton, self.view.dcRButton):
                rb.setAutoExclusive(False)
                rb.setChecked(False)
                rb.setAutoExclusive(True)
                rb.setVisible(False)
    # Helper function to reset baseline elements values
    def _reset_baseline_elements(self):
        for w in (self.view.baselineLabel_1, self.view.baselineLabel_2,
                  self.view.baselineCBox_1, self.view.baselineCBox_2):
            w.setVisible(False)
        self.view.baselineCBox_1.setValue(self.defaults["baselinewin1"])
        self.view.baselineCBox_2.setValue(self.defaults["baselinewin2"])


    def on_resample_click(self, checked):
        """
        Show or hide resampling controls based on the checkbox state. Resets resample frequency spinbox when disabled.
        """
        for w in [self.view.newfsLabel, self.view.resamplefsBox]:
            w.setVisible(checked)
        self.view.resampleLabel.setVisible(not checked)

        # Reset default values
        if not checked:
            self.view.resamplefsBox.setValue(self.defaults["resamplefs"])


    def update_next_button_state(self):
        """
        Enable or disable the 'Next' button based on the current segmentation mode and list content.
        Enables 'Next' if:
          * Event mode is selected and events exist.
            NOTE: Conditions will always exist (if no conditions, null condition will be created).
        Otherwise, disables the button.
        """
        has_events = self.view.eventList.model() and self.view.eventList.model().rowCount() > 0

        enable_next = self.view.conditionRButton.isChecked() or \
                      (self.view.eventRButton.isChecked() and has_events)
        self.view.main_window.nextButton.setEnabled(enable_next)


    def load_marks_from_file(self, file):
        """
        Loads and displays the available conditions and events from a single data file.
        Behavior:
            - Extracts conditions, events, and condition-event associations using an external function.
            - Introduces the condition and event list with unique values in the corresponding boxes.
            - Connects selection change signals to update the descriptive labels accordingly.
            - Handles and reports any errors encountered during file processing.
        """
        try:
            self.conditions, self.events, self.events_condition = marks_utils.extract_condition_events([file])

            # Set unique sorted conditions and events in models
            self.view.conditionList.setModel(QStringListModel(sorted(set(self.conditions))))
            self.view.eventList.setModel(QStringListModel(sorted(set(self.events))))

            # Connect selection changes to label updates
            self.view.conditionList.selectionModel().selectionChanged.connect(self.update_labels)
            self.view.eventList.selectionModel().selectionChanged.connect(self.update_labels)

            # Update next button state
            self.update_next_button_state()

        except Exception as e:
            import traceback
            traceback.print_exc()
            QtWidgets.QMessageBox.critical(self, "Error", f"An error occurred while loading conditions and events from the data:\n{e}")


    def update_labels(self):
        """
        Updates the UI labels displaying the selected conditions and events.
        Behavior:
            - Retrieves the user-selected items from both lists.
            - Displays a summary of selected items in the UI labels.
            - Enables the "Next" button.
        """

        selected_conditions = {index.data() for index in self.view.conditionList.selectionModel().selectedIndexes()}
        selected_events = {index.data() for index in self.view.eventList.selectionModel().selectedIndexes()}

        # Format and update labels
        cond_text = ", ".join(f"{cnd}" for cnd in selected_conditions) or "None"
        evt_text = ", ".join(f"{evt}" for evt in selected_events) or "None"

        self.view.conditionLabel.setText(f"Conditions: {cond_text}")
        self.view.eventLabel.setText(f"Events: {evt_text}")


    def get_segmentation_config(self):
        """
        Function that creates a dictionary with segmentation configurations.
        """
        # Get selected conditions/events
        selected_conditions = [
            index.data() for index in self.view.conditionList.selectionModel().selectedIndexes()
        ] if self.view.conditionList.selectionModel() else []
        selected_events = [
            index.data() for index in self.view.eventList.selectionModel().selectedIndexes()
        ] if self.view.eventList.selectionModel() else []

        # Create segmentation dictionary
        config = {
            # Type of segmentation
            "segmentation_type": "condition" if self.view.conditionRButton.isChecked() else "event" if self.view.eventRButton.isChecked() else None,
            # Selected conditions/events
            "selected_conditions": selected_conditions,
            "selected_events": selected_events if self.view.eventRButton.isChecked() else None,
            # Trial configuration
            "trial_length": self.view.trialBox.value() if self.view.conditionRButton.isChecked() else None,
            "trial_stride": self.view.trialstrideBox.value() if self.view.conditionRButton.isChecked() else None,
            "window_start": self.view.winBox_1.value() if self.view.eventRButton.isChecked() else None,
            "window_end": self.view.winBox_2.value() if self.view.eventRButton.isChecked() else None,
            # Normalization
            'norm': self.view.normCBox.isChecked() if self.view.normCBox else None,
            "norm_type": "z" if self.view.normCBox.isChecked() and self.view.zscoreRButton.isChecked() else
             "dc" if self.view.normCBox.isChecked() and self.view.dcRButton.isChecked() else None,
            "baseline_start": self.view.baselineCBox_1.value() if self.view.eventRButton.isChecked() and self.view.normCBox.isChecked() else None,
            "baseline_end": self.view.baselineCBox_2.value() if self.view.eventRButton.isChecked() and self.view.normCBox.isChecked() else None,
            'average': self.view.averageCBox.isChecked() if self.view.averageCBox else None,
            # Thresholding
            "thresholding": self.view.thresCBox.isChecked() if self.view.thresCBox else None,
            "thres_k": self.view.threskBox.value() if self.view.thresCBox.isChecked() else None,
            "thres_samples": self.view.thressampBox.value() if self.view.thresCBox.isChecked() else None,
            "thres_channels": self.view.threschanBox.value() if self.view.thresCBox.isChecked() else None,
            # Resample
            "resample": self.view.resampleCBox.isChecked() if self.view.resampleCBox else None,
            "resample_fs": self.view.resamplefsBox.value() if self.view.resampleCBox.isChecked() else None,
        }

        return config