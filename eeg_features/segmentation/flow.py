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
