from PyQt5 import QtWidgets, uic, QtCore
from Segmentation.utils import extract_condition_events
from PyQt5.QtCore import QStringListModel
from scipy.stats import norm
class SegmentationWidget(QtWidgets.QWidget):
    """
        Main windget element. Manages the  segmentation configuration of the data. Includes selection of signal markers
        (conditions/events), segmentation window settings, normalization, thresholding, and resampling options.
    """

    def __init__(self, main_window):
        super().__init__()
        uic.loadUi("Segmentation/segmentation_widget.ui", self)

        # Define variables
        self.main_window = main_window
        self.files = self.main_window.selected_files
        self.validating_window = False
        self.conditions = []
        self.events = []
        self.events_condition = []

        # Define the header (description) of the widget
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.topContentWidget = self.findChild(QtWidgets.QWidget, "topContentWidget")
        self.topContentWidget.setLayout(layout)
        self.segmentation_label = QtWidgets.QLabel()
        self.segmentation_label.setTextFormat(QtCore.Qt.RichText)
        self.segmentation_label.setWordWrap(True)
        self.segmentation_label.setText("""
            <div style="font-size: 11pt; font-family: Arial; line-height: 1;">
                <p>
                    Proceeding to the <b>Segmentation Module</b>, you can define how the signals should be split 
                    into analyzable segments. Choose between the following segmentation strategies:
            </div>
        """)
        layout.addWidget(self.segmentation_label)

        # --- GET ELEMENTS FROM UI MODULE ---

        # Conditions box
        self.conditionWidget = self.findChild(QtWidgets.QWidget, "conditionsWidget")
        self.availableconditionsLabel = self.findChild(QtWidgets.QLabel, "availableconditionsLabel")
        self.conditionList = self.findChild(QtWidgets.QListView, "conditionList")
        self.conditionLabel = self.findChild(QtWidgets.QLabel, "conditionLabel")
        # Events box
        self.eventWidget = self.findChild(QtWidgets.QWidget, "eventWidget")
        self.availableeventsLabel = self.findChild(QtWidgets.QLabel, "availableeventsLabel")
        self.eventList = self.findChild(QtWidgets.QListView, "eventList")
        self.eventLabel = self.findChild(QtWidgets.QLabel, "eventLabel")

        # Segmentation properties
        self.trials = self.findChild(QtWidgets.QVBoxLayout, "trials")
        self.segmentationtypeLabel = self.findChild(QtWidgets.QLabel, "segmentationtypeLabel")
        # Conditions
        self.conditionRButton = self.findChild(QtWidgets.QRadioButton, "conditionRButton")
        self.trialLabel = self.findChild(QtWidgets.QLabel, "trialLabel")
        self.trialBox = self.findChild(QtWidgets.QSpinBox, "trialBox")
        self.trialstrideLabel = self.findChild(QtWidgets.QLabel, "trialstrideLabel")
        self.trialstrideBox = self.findChild(QtWidgets.QSpinBox, "trialstrideBox")
        # Events
        self.eventRButton = self.findChild(QtWidgets.QRadioButton, "eventRButton")
        self.winLabel_1 = self.findChild(QtWidgets.QLabel, "winLabel_1")
        self.winBox_1 = self.findChild(QtWidgets.QSpinBox, "winBox_1")
        self.winLabel_2 = self.findChild(QtWidgets.QLabel, "winLabel_2")
        self.winBox_2 = self.findChild(QtWidgets.QSpinBox, "winBox_2")

        # Normalization
        self.normLabel = self.findChild(QtWidgets.QLabel, "normLabel")
        self.normCBox = self.findChild(QtWidgets.QCheckBox, "normCBox")
        self.zscoreRButton = self.findChild(QtWidgets.QRadioButton, "zscoreRButton")
        self.dcRButton = self.findChild(QtWidgets.QRadioButton, "dcRButton")
        # Baseline information
        self.baselineLabel_1 = self.findChild(QtWidgets.QLabel, "baselineLabel_1")
        self.baselineCBox_1 = self.findChild(QtWidgets.QSpinBox, "baselineCBox_1")
        self.baselineLabel_2 = self.findChild(QtWidgets.QLabel, "baselineLabel_2")
        self.baselineCBox_2 = self.findChild(QtWidgets.QSpinBox, "baselineCBox_2")

        # Average epochs
        self.averageCBox = self.findChild(QtWidgets.QCheckBox, "averageCBox")

        # Thresholding
        self.thresCBox = self.findChild(QtWidgets.QCheckBox, "thresCBox")
        self.threskLabel = self.findChild(QtWidgets.QLabel, "threskLabel")
        self.threskBox = self.findChild(QtWidgets.QDoubleSpinBox, "threskBox")
        self.threskLabelaux = self.findChild(QtWidgets.QLabel, "threskLabelaux")
        self.thressampLabel = self.findChild(QtWidgets.QLabel, "thressampLabel")
        self.thressampBox = self.findChild(QtWidgets.QSpinBox, "thressampBox")
        self.threschanLabel = self.findChild(QtWidgets.QLabel, "threschanLabel")
        self.threschanBox = self.findChild(QtWidgets.QSpinBox, "threschanBox")
        self.threshelButton = self.findChild(QtWidgets.QToolButton, "threshelButton")

        # Resampling
        self.resampleCBox = self.findChild(QtWidgets.QCheckBox, "resampleCBox")
        self.newfsLabel = self.findChild(QtWidgets.QLabel, "newfsLabel")
        self.resamplefsBox = self.findChild(QtWidgets.QSpinBox, "resamplefsBox")

        # --- ELEMENT SETUP ---

        # Condition and event boxes (allow multiple selection)
        self.conditionList.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.eventList.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # Radio buttons should be exclusive within their groups (groups are defined based on their parent)
        self.conditionRButton.setAutoExclusive(True)
        self.eventRButton.setAutoExclusive(True)
        self.zscoreRButton.setAutoExclusive(True)
        self.dcRButton.setAutoExclusive(True)


        # Conditions/Events
        self.conditionRButton.clicked.connect(self.handle_segmentation_toggle)
        self.eventRButton.clicked.connect(self.handle_segmentation_toggle)
        # self.winBox_2.editingFinished.connect(self.validate_window_interval)
        self.eventList.setEnabled(False)
        self.conditionList.setEnabled(False)
        self.trialBox.editingFinished.connect(self.update_max_samples)
        self.winBox_1.editingFinished.connect(self.update_max_samples)
        self.winBox_2.editingFinished.connect(self.update_max_samples)


        # Normalization
        self.normCBox.toggled.connect(self.toggle_normalization_events_controls)
        # self.baselineCBox_2.editingFinished.connect(lambda: self.validate_window_interval(self.baselineCBox_1, self.baselineCBox_2))

        # Thresholding
        self.thresCBox.toggled.connect(self.toggle_threshold_controls)
        self.threshelButton.clicked.connect(self.show_threshold_help)
        self.threskBox.editingFinished.connect(self.set_sigma_percent)
        # Set initial values for threshold spin boxes
        self.threskBox.setValue(self.threskBox.minimum())
        self.thressampBox.setValue(self.thressampBox.minimum())
        self.threschanBox.setValue(self.threschanBox.minimum())

        # Resample
        self.resampleCBox.toggled.connect(self.toggle_resample_controls)

        # Hide advanced options by default
        for widget in [
            self.zscoreRButton, self.dcRButton,
            self.baselineLabel_1, self.baselineCBox_1,
            self.baselineLabel_2, self.baselineCBox_2,
            self.threskLabel, self.threskBox, self.threskLabelaux,
            self.thressampLabel, self.thressampBox,
            self.threschanLabel, self.threschanBox,
            self.threshelButton, self.newfsLabel, self.resamplefsBox,
        ]:
            widget.setVisible(False)

        self.update_checkboxes_state()


    def load_and_display_events_from_file(self, file):
        """
            Loads and displays the available conditions and events from a single data file.
            Behavior:
                - Extracts conditions, events, and condition-event associations using an external function.
                - Populates the condition and event list with unique values.
                - Connects selection change signals to update the descriptive labels accordingly.
                - Handles and reports any errors encountered during file processing.
        """
        try:
            self.conditions, self.events, self.events_condition = extract_condition_events([file])

            # Set unique sorted conditions and events in models
            self.conditionList.setModel(QStringListModel(sorted(set(self.conditions))))
            self.eventList.setModel(QStringListModel(sorted(set(self.events))))

            # Connect selection changes to label updates
            self.conditionList.selectionModel().selectionChanged.connect(self.update_labels)
            self.eventList.selectionModel().selectionChanged.connect(self.update_labels)
            self.update_labels()

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

        selected_conditions = {index.data() for index in self.conditionList.selectionModel().selectedIndexes()}
        selected_events = {index.data() for index in self.eventList.selectionModel().selectedIndexes()}

        # # Count conditions globally
        # condition_counter = Counter(self.conditions)
        # counted_conditions = ([(cnd, condition_counter[cnd]) for cnd in selected_conditions] if selected_conditions else list(
        #         condition_counter.items()))
        #
        # # Filter events by selected conditions if any, then count
        # if selected_conditions:
        #     filtered_events = (self.events[i] for i, cond in enumerate(self.events_condition) if cond in selected_conditions)
        #     event_counter = Counter(filtered_events)
        # else:
        #     event_counter = Counter(self.events)
        #
        # counted_events = ([(evt, event_counter[evt]) for evt in selected_events if evt in event_counter] if selected_events else list(
        #         event_counter.items()))
        #
        # # Format and update labels
        # cond_text = ", ".join(f"{cnd} ({cnt})" for cnd, cnt in counted_conditions) or "None"
        # evt_text = ", ".join(f"{evt} ({cnt})" for evt, cnt in counted_events) or "None"

        # Format and update labels
        cond_text = ", ".join(f"{cnd}" for cnd in selected_conditions) or "None"
        evt_text = ", ".join(f"{evt}" for evt in selected_events) or "None"

        self.conditionLabel.setText(f"Conditions: {cond_text}")
        self.eventLabel.setText(f"Events: {evt_text}")
        self.update_next_button_state()

    def handle_segmentation_toggle(self):
        """
            Handle toggling to 'condition' or 'event' segmentation mode.
        """
        # Condition
        if self.conditionRButton.isChecked():
            self.eventRButton.setChecked(False)
            self.on_condition_button_clicked()
            self.show_condition_widgets()
            self.reset_trial_params()
            self._post_toggle_updates()
            self.normLabel.setText('- Over condition segment')
        # Event
        if self.eventRButton.isChecked():
            self.conditionRButton.setChecked(False)
            self.on_event_button_clicked()
            self.show_event_widgets()
            self.reset_win_params()
            self._post_toggle_updates()
            self.normLabel.setText('- Over event window')
        self.toggle_normalization_events_controls(self.normCBox.isChecked())

    # def handle_condition_toggle(self):
    #     """
    #         Handle toggling to 'condition' segmentation mode.
    #     """
    #     if self.conditionRButton.isChecked():
    #         self.eventRButton.setChecked(False)
    #         self.on_condition_button_clicked()
    #         self.show_condition_widgets()
    #         self.reset_trial_params()
    #         self._post_toggle_updates()
    #
    #
    # def handle_event_toggle(self):
    #     """
    #         Handle toggling to 'event' segmentation mode.
    #     """
    #     if self.eventRButton.isChecked():
    #         self.conditionRButton.setChecked(False)
    #         self.on_event_button_clicked()
    #         self.show_event_widgets()
    #         self.reset_win_params()
    #         self._post_toggle_updates()


    def on_condition_button_clicked(self):
        """
            Enable segmentation by condition: activate condition selectors and disable events.
        """
        self._set_event_widgets_enabled(False)
        self._set_condition_widgets_enabled(True)
        self.main_window.nextButton.setEnabled(True)


    def on_event_button_clicked(self):
        """
            Enable segmentation by event: activate event selectors (conditions remain enabled).
        """
        self._set_event_widgets_enabled(True)
        self.main_window.nextButton.setEnabled(True)


    def _post_toggle_updates(self):
        """
            Updates associated with toggles
        """
        self.update_next_button_state()
        self.update_checkboxes_state()
        # self.normCBox.setChecked(False)


    def update_next_button_state(self):
        """
            Enable or disable the 'Next' button based on the current segmentation mode and list content.
            - Enables 'Next' if:
              * Event mode is selected and events exist.
              NOTE: Conditions will always exist (if no conditions, null condition will be created).
            Otherwise, disables the button.
        """
        has_events = self.eventList.model() and self.eventList.model().rowCount() > 0

        enable_next = self.conditionRButton.isChecked() or \
                      (self.eventRButton.isChecked() and has_events)
        self.main_window.nextButton.setEnabled(enable_next)


    def update_checkboxes_state(self):
        """
            Enable or disable resample, threshold, normalization, and average checkboxes
            based on whether a segmentation mode (condition or event) is selected.
        """
        enabled = self.conditionRButton.isChecked() or self.eventRButton.isChecked()
        for box in (self.resampleCBox, self.thresCBox, self.normCBox, self.averageCBox):
            box.setEnabled(enabled)

    # Helper functions for enabling and disabling elements when toggling of checking (or unchecking) checkboxes for
    # condition and events widgets
    def _set_event_widgets_enabled(self, enabled: bool):
        self.eventList.setEnabled(enabled)
        self.availableeventsLabel.setEnabled(enabled)
        self.eventLabel.setEnabled(enabled)
        self.conditionList.setEnabled(enabled)
        self.conditionLabel.setEnabled(enabled)
    def _set_condition_widgets_enabled(self, enabled: bool):
        self.conditionList.setEnabled(enabled)
        self.availableconditionsLabel.setEnabled(enabled)
        self.conditionLabel.setEnabled(enabled)
    def hide_all_param_widgets(self):
        for w in [self.trialLabel, self.trialBox, self.trialstrideLabel, self.trialstrideBox, self.winLabel_1, self.winBox_1, self.winLabel_2, self.winBox_2]: w.hide()
    def show_event_widgets(self):
        for w in [self.winLabel_1, self.winBox_1, self.winLabel_2, self.winBox_2]: w.show()
        for w in [self.trialLabel, self.trialBox, self.trialstrideLabel, self.trialstrideBox]: w.hide()
    def show_condition_widgets(self):
        for w in [self.trialLabel, self.trialBox, self.trialstrideLabel, self.trialstrideBox]: w.show()
        for w in [self.winLabel_1, self.winBox_1, self.winLabel_2, self.winBox_2]: w.hide()
    # def show_all_widgets(self):
    #     for w in [self.winLabel_1, self.winBox_1, self.winLabel_2, self.winBox_2, self.trialLabel, self.trialBox]: w.show()


    def reset_segmentation_state(self):
        """
        Reset the segmentation UI and state to default:
        - Uncheck segmentation mode radio buttons.
        - Clear condition and event lists.
        - Reset labels and parameters.
        - Hide parameter widgets.
        - Reset thresholding and resampling controls.
        - Disable 'Next' button.
        """
        # Disable both RadButtons. To this ende, temporarily disable AutoExclusive is necessary
        for btn in (self.conditionRButton, self.eventRButton):
            btn.setAutoExclusive(False)
            btn.setChecked(False)
            btn.setAutoExclusive(True)

        # Clear condition and event models
        empty_model = QStringListModel()
        self.conditionList.setModel(empty_model)
        self.eventList.setModel(empty_model)

        # Reset labels and UI elements
        self.conditionLabel.setText("Conditions: None")
        self.eventLabel.setText("Events: None")
        self.hide_all_param_widgets()
        self.reset_trial_params()
        self.reset_win_params()

        # Hide thresholding and resampling widgets and reset their states/values
        widgets_to_hide = [
            self.resamplefsBox, self.newfsLabel,
            self.threskBox, self.threschanBox, self.thressampBox,
            self.threskLabel, self.threskLabelaux, self.threschanLabel, self.thressampLabel,
            self.threshelButton
        ]
        for w in widgets_to_hide:
            w.setVisible(False)

        for checkbox in [self.thresCBox, self.resampleCBox, self.normCBox, self.averageCBox]:
            checkbox.setChecked(False)

        # Reset spinbox values to minimum
        for spinbox in [self.resamplefsBox, self.threskBox, self.threschanBox, self.thressampBox]:
            spinbox.setValue(spinbox.minimum())

        # Disable the Next button and update checkboxes states accordingly
        self.update_next_button_state()
        self.update_checkboxes_state()
    # Helpers to reset SpinBoxes values
    def reset_trial_params(self):
        self.trialBox.setValue(self.trialBox.minimum())
    def reset_win_params(self):
        self.winBox_1.setValue(0)
        self.winBox_2.setValue(0)


    def toggle_threshold_controls(self, checked):
        """
            Show or hide threshold-related controls based on the checkbox state.
            Resets spinboxes to minimum values when disabled.
        """

        for w in [self.threskLabel, self.threskBox, self.threskLabelaux, self.thressampLabel, self.thressampBox, self.threschanLabel,
                   self.threschanBox, self.threshelButton]:
            w.setVisible(checked)

        if not checked:
            for box in (self.threskBox, self.thressampBox, self.threschanBox):
                box.setValue(box.minimum())


    def toggle_normalization_events_controls(self, checked):
        """
            Show or hide normalization controls based on the checkbox state and segmentation mode.
            Resets baseline spinboxes and radio buttons when normalization is disabled.
        """
        def reset_baseline():
            for w in (self.baselineLabel_1, self.baselineLabel_2, self.baselineCBox_1, self.baselineCBox_2):
                w.setVisible(False)
            self.baselineCBox_1.setValue(0)
            self.baselineCBox_2.setValue(0)

        for w in (self.zscoreRButton, self.dcRButton):
            w.setVisible(checked)

        if checked:
            if self.eventRButton.isChecked():
                for w in (
                self.baselineLabel_1, self.baselineLabel_2, self.baselineCBox_1, self.baselineCBox_2):
                    w.setVisible(True)
            elif self.conditionRButton.isChecked():
                reset_baseline()
        else:
            reset_baseline()
            for rb in (self.zscoreRButton, self.dcRButton):
                rb.setAutoExclusive(False)
                rb.setChecked(False)
                rb.setAutoExclusive(True)
                rb.setVisible(False)


    def toggle_resample_controls(self, checked):
        """
            Show or hide resampling controls based on the checkbox state. Resets resample frequency spinbox when disabled.
        """
        for w in [self.newfsLabel, self.resamplefsBox]:
            w.setVisible(checked)
        if not checked:
            self.resamplefsBox.setValue(self.resamplefsBox.minimum())


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


    # def validate_window_interval(self, hnd_1, hnd_2):
    #     """
    #         Ensure that the event window interval (start < end) is valid.
    #         Resets to default values and warns the user if invalid.
    #     """
    #     if not (hnd_1.isEnabled() and hnd_2.isEnabled()):
    #         return
    #
    #     start, end = hnd_1.value(), hnd_2.value()
    #     if end <= start:
    #         for box in (hnd_1, hnd_2):
    #             box.blockSignals(True)
    #         QtWidgets.QMessageBox.warning(self, "Invalid Time Window",
    #                                       "End time must be greater than start time.")
    #         hnd_1.setValue(0)
    #         hnd_2.setValue(1)
    #         for box in (hnd_1, hnd_2):
    #             box.blockSignals(False)


    # def validate_window_interval(self):
    #     """
    #         Ensure that the event window interval (start < end) is valid.
    #         Resets to default values and warns the user if invalid.
    #     """
    #     if not (self.winBox_1.isEnabled() and self.winBox_2.isEnabled()):
    #         return
    #
    #     start, end = self.winBox_1.value(), self.winBox_2.value()
    #     if end <= start:
    #         for box in (self.winBox_1, self.winBox_2):
    #             box.blockSignals(True)
    #         QtWidgets.QMessageBox.warning(self, "Invalid Time Window",
    #                                       "End time must be greater than start time.")
    #         self.winBox_1.setValue(0)
    #         self.winBox_2.setValue(1)
    #         for box in (self.winBox_1, self.winBox_2):
    #             box.blockSignals(False)
    # def validate_baseline_window_interval(self):
    #     """
    #     Ensure that the baseline window interval (start < end) is valid.
    #     Resets to default values and warns the user if invalid.
    #     """
    #     if not (self.baselineCBox_1.isEnabled() and self.baselineCBox_2.isEnabled()):
    #         return
    #
    #     start, end = self.baselineCBox_1.value(), self.baselineCBox_2.value()
    #     if end <= start:
    #         for box in (self.baselineCBox_1, self.baselineCBox_2):
    #             box.blockSignals(True)
    #         QtWidgets.QMessageBox.warning(self, "Invalid Time Baseline Window",
    #                                       "End time must be greater than start time.")
    #         self.baselineCBox_1.setValue(0)
    #         self.baselineCBox_2.setValue(1)
    #         for box in (self.baselineCBox_1, self.baselineCBox_2):
    #             box.blockSignals(False)

    def update_max_samples(self):
        if self.conditionRButton.isChecked():
            max_samples = (self.trialBox.value()/1000) * self.main_window.sampling_frequency
        else:
            max_samples = -self.winBox_1.value() + self.winBox_2.value()
            max_samples = (max_samples/1000) * self.main_window.sampling_frequency
        self.thressampBox.setMaximum(int(max_samples))

    def set_sigma_percent(self):
        percent = norm.cdf(self.threskBox.value()) - norm.cdf(-self.threskBox.value())
        percent *= 100
        self.threskLabelaux.setText(f"{percent:.2f}%")

    def get_segmentation_config(self):
        """
            Function that creates a dictionary with segmentation configurations.
        """

        # Get selected conditions/events
        selected_conditions = [
            index.data() for index in self.conditionList.selectionModel().selectedIndexes()
        ] if self.conditionList.selectionModel() else []
        selected_events = [
            index.data() for index in self.eventList.selectionModel().selectedIndexes()
        ] if self.eventList.selectionModel() else []

        # Create segmentation dictionary
        config = {
            "segmentation_type": "condition" if self.conditionRButton.isChecked() else "event" if self.eventRButton.isChecked() else None,

            "selected_conditions": selected_conditions,
            "selected_events": selected_events if self.eventRButton.isChecked() else None,

            "trial_length": self.trialBox.value() if self.conditionRButton.isChecked() else None,
            "trial_stride": self.trialstrideBox.value() if self.conditionRButton.isChecked() else None,
            "window_start": self.winBox_1.value() if self.eventRButton.isChecked() else None,
            "window_end": self.winBox_2.value() if self.eventRButton.isChecked() else None,
            'norm': self.normCBox.isChecked() if self.normCBox else None,
            "norm_type": "z" if self.normCBox.isChecked() and self.zscoreRButton.isChecked() else
             "dc" if self.normCBox.isChecked() and self.dcRButton.isChecked() else None,
            "baseline_start": self.baselineCBox_1.value() if self.eventRButton.isChecked() and self.normCBox.isChecked() else None,
            "baseline_end": self.baselineCBox_2.value() if self.eventRButton.isChecked() and self.normCBox.isChecked() else None,
            'average': self.averageCBox.isChecked() if self.averageCBox else None,

            "thresholding": self.thresCBox.isChecked() if self.thresCBox else None,
            "thres_k": self.threskBox.value() if self.thresCBox.isChecked() else None,
            "thres_samples": self.thressampBox.value() if self.thresCBox.isChecked() else None,
            "thres_channels": self.threschanBox.value() if self.thresCBox.isChecked() else None,

            "resample": self.resampleCBox.isChecked() if self.resampleCBox else None,
            "resample_fs": self.resamplefsBox.value() if self.resampleCBox.isChecked() else None,
        }

        return config







