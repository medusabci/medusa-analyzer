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
        "broadband_min": float(controller.view.minbroadLabel.text()),
        "broadband_max": float(controller.view.maxbroadLabel.text()),
        "apply_preprocessing": True if controller.view.preprocessingButton.isChecked() else None,

        "baseline": controller.view.baselineCBox.isChecked() if controller.view.baselineCBox else None,
        "baseline_cutoff": controller.view.cutoffbaselineBox.value() if controller.view.baselineCBox.isChecked() else None,
        "baseline_order": controller.view.orderbaselineBox.value() if controller.view.baselineCBox.isChecked() else None,
        "baseline_win": controller.view.winbaselineBox.currentText() if controller.view.baselineCBox.isChecked() else None,

        "bandpass": controller.view.bpCBox.isChecked() if controller.view.bpCBox else None,
        "bp_min": controller.view.minfreqbpBox.value() if controller.view.bpCBox.isChecked() else None,
        "bp_max": controller.view.maxfreqbpBox.value() if controller.view.bpCBox.isChecked() else None,
        "bp_order": controller.view.orderbpBox.value() if controller.view.bpCBox.isChecked() else None,
        "bp_win": controller.view.winbpBox.currentText() if controller.view.bpCBox.isChecked() else None,

        "norm": controller.view.normCBox.isChecked() if controller.view.normCBox else None,

        "hrv": True if controller.view.hrvCBox.isChecked() else None,
        "interpolation_method": controller.view.hrvinterpolBox.currentText() if controller.view.hrvCBox.isChecked() else None,
        "min_rr_time": controller.view.minrrBox.value() if controller.view.rrcorrectionCBox.isChecked() else None,
        "max_rr_time": controller.view.maxrrBox.value() if controller.view.rrcorrectionCBox.isChecked() else None,
        "correction_method": controller.view.rrmethodBox.currentText() if controller.view.rrcorrectionCBox.isChecked() else None,
        "resample_fs": controller.view.resamplefsBox.value() if controller.view.resampleCBox.isChecked() else None,
    }
    return config

def on_next_click(view):
    """
    Handles the event when the "Next" button is clicked. It initializes the segmentation widget with the information of
    the events and conditions of the selected file
    """
    # If preprocessing is enabled, ensure at least one preprocessing option is selected
    if view.preprocessingButton.isChecked() and not (
            view.normCBox.isChecked() or view.bpCBox.isChecked() or view.baselineCBox.isChecked()):
        QtWidgets.QMessageBox.critical(
            view,
            "Invalid configuration",
            "You must select at least one filtering option (Norm, Baseline, or Bandpass) when preprocessing is enabled. "
            "Alternatively, disable \"Preprocess data\" to proceed without filtering."
        )
        return False

    # If not HRV, ensure that the corresponding parameters are disabled
    current_idx = view.main_window.stackedWidget.currentIndex()
    next_widget = view.main_window.stackedWidget.widget(current_idx + 1)
    if not view.hrvCBox.isChecked():
        next_widget.toolBox.widget(0).setDisabled(True) # widget (0) is the HRV page
    else:
        next_widget.toolBox.widget(0).setDisabled(False)


    # Save config
    view.main_window.controller.preproc_config = get_preprocessing_config(view.controller)

    return True
