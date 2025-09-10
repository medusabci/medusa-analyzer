from PySide6.QtCore import QStringListModel


def reset_segmentation_state(controller):
    """
    Reset the segmentation UI and state to default:
        - Check the condition radio button
        - Clear condition and event lists.
        - Reset labels and parameters.
        - Hide parameter widgets.
        - Reset thresholding and resampling controls.
        - Disable 'Next' button.
    """

    # Check the condition radio button
    controller.view.conditionRButton.setChecked(True)

    # Clear condition and event lists
    empty_model = QStringListModel()
    controller.view.conditionList.setModel(empty_model)
    controller.view.eventList.setModel(empty_model)
    # Reset labels and UI elements
    controller.view.conditionLabel.setText("Conditions: None")
    controller.view.eventLabel.setText("Events: None")
    controller._event_element_visibility(False)
    controller._reset_segmentation_params()

    # Disable checkboxes
    for checkbox in [controller.view.normCBox, controller.view.thresCBox, controller.view.resampleCBox, controller.view.averageCBox]:
        checkbox.setChecked(False)

    # Hide normalization, thresholding and resampling elements
    elements = [
        controller.view.zscoreRButton, controller.view.dcRButton,
        controller.view.threskBox, controller.view.threschanBox, controller.view.thressampBox,
        controller.view.threskLabel, controller.view.threskLabelaux, controller.view.threschanLabel, controller.view.thressampLabel,
        controller.view.threshelpButton,
        controller.view.resamplefsBox, controller.view.newfsLabel
    ]
    for w in elements:
        w.setVisible(False)

    # Show descriptive labels
    elements = [
        controller.view.thresLabel, controller.view.normLabel, controller.view.resampleLabel
    ]
    for w in elements:
        w.setVisible(True)

    # Reset spinboxes values to default
    controller.view.threskBox.setValue(controller.defaults["threshold"])
    controller.view.threschanBox.setValue(controller.defaults["threschannels"])
    controller.view.thressampBox.setValue(controller.defaults["thressamples"])
    controller.view.resamplefsBox.setValue(controller.defaults["resamplefs"])

    # Update the next button state
    controller.update_next_button_state()


def get_segmentation_config(controller):
    """
    Function that creates a dictionary with segmentation configurations.
    """
    # Get selected conditions/events
    selected_conditions = [
        index.data() for index in controller.view.conditionList.selectionModel().selectedIndexes()
    ] if controller.view.conditionList.selectionModel() else []
    selected_events = [
        index.data() for index in controller.view.eventList.selectionModel().selectedIndexes()
    ] if controller.view.eventList.selectionModel() else []

    # Create segmentation dictionary
    config = {
        # Type of segmentation
        "segmentation_type": "condition" if controller.view.conditionRButton.isChecked() else "event" if controller.view.eventRButton.isChecked() else None,
        # Selected conditions/events
        "selected_conditions": selected_conditions,
        "selected_events": selected_events if controller.view.eventRButton.isChecked() else None,
        # Trial configuration
        "trial_length": controller.view.trialBox.value() if controller.view.conditionRButton.isChecked() else None,
        "trial_stride": controller.view.trialstrideBox.value() if controller.view.conditionRButton.isChecked() else None,
        "window_start": controller.view.winBox_1.value() if controller.view.eventRButton.isChecked() else None,
        "window_end": controller.view.winBox_2.value() if controller.view.eventRButton.isChecked() else None,
        # Normalization
        'norm': controller.view.normCBox.isChecked() if controller.view.normCBox else None,
        "norm_type": "z" if controller.view.normCBox.isChecked() and controller.view.zscoreRButton.isChecked() else
         "dc" if controller.view.normCBox.isChecked() and controller.view.dcRButton.isChecked() else None,
        "baseline_start": controller.view.baselineCBox_1.value() if controller.view.eventRButton.isChecked() and controller.view.normCBox.isChecked() else None,
        "baseline_end": controller.view.baselineCBox_2.value() if controller.view.eventRButton.isChecked() and controller.view.normCBox.isChecked() else None,
        'average': controller.view.averageCBox.isChecked() if controller.view.averageCBox else None,
        # Thresholding
        "thresholding": controller.view.thresCBox.isChecked() if controller.view.thresCBox else None,
        "thres_k": controller.view.threskBox.value() if controller.view.thresCBox.isChecked() else None,
        "thres_samples": controller.view.thressampBox.value() if controller.view.thresCBox.isChecked() else None,
        "thres_channels": controller.view.threschanBox.value() if controller.view.thresCBox.isChecked() else None,
        # Resample
        "resample": controller.view.resampleCBox.isChecked() if controller.view.resampleCBox else None,
        "resample_fs": controller.view.resamplefsBox.value() if controller.view.resampleCBox.isChecked() else None,
    }

    return config