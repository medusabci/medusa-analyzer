from PySide6 import QtWidgets

def reset_all_controls(controller):
    """
    Hides all elements of the data preprocessing groupbox and resets them to defaults.
    Called at:
        - Analyzer startup
        - When 'Preprocess data' is unchecked
        - When files are deleted
    """

    # Widgets to hide
    widgets_to_hide = [
        controller.view.baselineLabel, controller.view.baselineCBox, controller.view.cutoffbaselineLabel, controller.view.cutoffbaselineBox,
        controller.view.winbaselineLabel, controller.view.winbaselineBox,
        controller.view.orderbaselineLabel, controller.view.orderbaselineBox,
        controller.view.bpLabel, controller.view.bpCBox, controller.view.bpminfreqLabel, controller.view.minfreqbpBox,
        controller.view.bpmaxfreqLabel, controller.view.maxfreqbpBox, controller.view.orderbpLabel, controller.view.orderbpBox,
        controller.view.winbpLabel, controller.view.winbpBox,
        controller.view.normLabel, controller.view.normCBox,
        controller.view.baselinePlotWidget, controller.view.bandpassPlotWidget,
        controller.view.bpgroupBox, controller.view.normgroupBox, controller.view.baselinegroupBox,
        controller.view.drawbaselineButton, controller.view.drawbpButton,
    ]
    for w in widgets_to_hide:
        w.setVisible(False)

    # Reset checkboxes
    for box in (controller.view.baselineCBox, controller.view.bpCBox, controller.view.normCBox, controller.view.preprocessingButton):
        box.setChecked(False)

    # Reset spinboxes using defaults
    spinbox_defaults = {
        controller.view.cutoffbaselineBox: "cutoffbaseline",
        controller.view.orderbaselineBox: "orderbaseline",
        controller.view.minfreqbpBox: "minfreqbp",
        controller.view.maxfreqbpBox: "maxfreqbp",
        controller.view.orderbpBox: "orderbp",
    }
    for box, key in spinbox_defaults.items():
        box.setValue(controller.view.defaults[key])

def get_preprocessing_config(controller):
    """
    Function that creates a dictionary with preprocessing configurations.
    """
    config = {
        "fs": controller.view.main_window.stackedWidget.widget(1).controller.biosignal_info['fs'],

        "clean": True if controller.view.cleanCBox.isChecked() else None,
        "clean_method": controller.view.cleanBox.currentText() if controller.view.cleanCBox.isChecked() else None,
        "zscore": True if controller.view.zscoreCBox.isChecked() else None,

        "hrv": True if controller.view.hrvCBox.isChecked() else None,
        "processing_method": controller.view.hrvprocessBox.currentText() if controller.view.hrvCBox.isChecked() else None,
        "correct_artifacts": True if (controller.view.artifactsCBox.isChecked() and controller.view.hrvCBox.isChecked()) else False,
        "resample_fs": controller.view.resampleBox.value() if controller.view.hrvCBox.isChecked() else None,
    }
    return config

def on_next_click(view):
    """
    Handles the event when the "Next" button is clicked. It initializes the segmentation widget with the information of
    the events and conditions of the selected file
    """

    # If HRV is checked but Clean is not -> warn the user
    if view.hrvCBox.isChecked() and not view.cleanCBox.isChecked():
        msg_box = QtWidgets.QMessageBox()
        msg_box.setIcon(QtWidgets.QMessageBox.Warning)
        msg_box.setWindowTitle("Warning: Uncleaned Signal")
        msg_box.setText(
            "You have selected HRV analysis without enabling signal cleaning.\n\n"
            "Peak detection may fail or produce incorrect results if the ECG signal is not cleaned.\n\n"
            "Do you want to continue anyway?"
        )
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        msg_box.setDefaultButton(QtWidgets.QMessageBox.No)
        response = msg_box.exec()

        # If user chooses "No", cancel navigation
        if response == QtWidgets.QMessageBox.No:
            return False

    # If not HRV, ensure that the corresponding parameters are disabled
    current_idx = view.main_window.stackedWidget.currentIndex()
    parameters = view.main_window.stackedWidget.widget(current_idx + 1)
    if not view.hrvCBox.isChecked():
        parameters.toolBox.widget(0).setDisabled(True) # widget (0) is the HRV page
    else:
        parameters.toolBox.widget(0).setDisabled(False)

    # Save config
    view.main_window.controller.preproc_config = get_preprocessing_config(view.controller)

    return True
