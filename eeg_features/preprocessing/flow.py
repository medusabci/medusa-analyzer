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
        controller.view.notchfilterLabel, controller.view.notchCBox, controller.view.notchminLabel, controller.view.minfreqnotchBox,
        controller.view.notchmaxLabel, controller.view.maxfreqnotchBox, controller.view.winnotchLabel, controller.view.winnotchBox,
        controller.view.orderNotchLabel, controller.view.orderNotchBox,
        controller.view.bpLabel, controller.view.bpCBox, controller.view.bpminfreqLabel, controller.view.minfreqbpBox,
        controller.view.bpmaxfreqLabel, controller.view.maxfreqbpBox, controller.view.orderbpLabel, controller.view.orderbpBox,
        controller.view.winbpLabel, controller.view.winbpBox,
        controller.view.carLabel, controller.view.carCBox,
        controller.view.notchPlotWidget, controller.view.bandpassPlotWidget,
        controller.view.bpgroupBox, controller.view.cargroupBox, controller.view.notchgroupBox,
        controller.view.drawnotchButton, controller.view.drawbpButton,
    ]
    for w in widgets_to_hide:
        w.setVisible(False)

    # Reset checkboxes
    for box in (controller.view.notchCBox, controller.view.bpCBox, controller.view.carCBox, controller.view.preprocessingButton):
        box.setChecked(False)

    # Reset spinboxes using defaults
    spinbox_defaults = {
        controller.view.minfreqnotchBox: "minfreqnotch",
        controller.view.maxfreqnotchBox: "maxfreqnotch",
        controller.view.orderNotchBox: "ordernotch",
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
        "band_segmentation": True if controller.view.bandCBox.isChecked() else None,
        "broadband_min": controller.view.minbroadBox.value(),
        "broadband_max": controller.view.maxbroadBox.value(),
        "selected_bands": (
            None
            if (not controller.view.bandCBox.isChecked() or (
                    len(controller.view.selected_bands_by_type.get("segmentation", [])) == 1 and
                    str(controller.view.selected_bands_by_type.get("segmentation", [])[0].get("name",
                                                                                        "")).lower() == "broadband"
            ))
            else controller.view.selected_bands_by_type.get("segmentation", [])
        ),
        "apply_preprocessing": True if controller.view.preprocessingButton.isChecked() else None,

        "notch": controller.view.notchCBox.isChecked() if controller.view.notchCBox else None,
        "notch_min": controller.view.minfreqnotchBox.value() if controller.view.notchCBox.isChecked() else None,
        "notch_max": controller.view.maxfreqnotchBox.value() if controller.view.notchCBox.isChecked() else None,
        "notch_order": controller.view.orderNotchBox.value() if controller.view.notchCBox.isChecked() else None,
        "notch_win": controller.view.winnotchBox.currentText() if controller.view.notchCBox.isChecked() else None,

        "bandpass": controller.view.bpCBox.isChecked() if controller.view.bpCBox else None,
        "bp_min": controller.view.minfreqbpBox.value() if controller.view.bpCBox.isChecked() else None,
        "bp_max": controller.view.maxfreqbpBox.value() if controller.view.bpCBox.isChecked() else None,
        "bp_order": controller.view.orderbpBox.value() if controller.view.bpCBox.isChecked() else None,
        "bp_win": controller.view.winbpBox.currentText() if controller.view.bpCBox.isChecked() else None,

        "car": controller.view.carCBox.isChecked() if controller.view.carCBox else None,
    }
    return config

def on_next_click(view):
    """
    Handles the event when the "Next" button is clicked. It initializes the segmentation widget with the information of
    the events and conditions of the selected file
    """
    # If preprocessing is enabled, ensure at least one preprocessing option is selected
    if view.preprocessingButton.isChecked() and not (
            view.carCBox.isChecked() or view.bpCBox.isChecked() or view.notchCBox.isChecked()):
        QtWidgets.QMessageBox.critical(
            view,
            "Invalid configuration",
            "You must select at least one filtering option (CAR, Bandpass, or Notch) when preprocessing is enabled. "
            "Alternatively, disable \"Preprocess data\" to proceed without filtering."
        )
        return False

    # If band segmentation is selected, ensure at least one band is chosen
    if view.bandCBox.isChecked() and view.bandLabel.text() == 'None':
        QtWidgets.QMessageBox.critical(view, "Error", "Please, select at least one frequency band for segmentation, or uncheck \"Band filtering\" selection.")
        return False

    # Notch inside bandpass
    if view.bpCBox.isChecked() and view.notchCBox.isChecked():
        if not (view.minfreqbpBox.value() <= view.minfreqnotchBox.value() <= view.maxfreqbpBox.value()
            and view.minfreqbpBox.value() <= view.maxfreqnotchBox.value() <= view.maxfreqbpBox.value()):

            QtWidgets.QMessageBox.warning(view, "Invalid notch",
                                          f"Notch is outside bandpass range. Please adjust or disable it before proceeding.")
            return False



    # Get the next widget (that will be the segmentation widget)
    idx = view.main_window.stackedWidget.currentIndex()
    segmentation = view.main_window.stackedWidget.widget(idx + 1)
    # Initialize the segmentation widget
    files_controller_widget = view.main_window.stackedWidget.widget(idx - 1).controller
    segmentation.controller.load_marks_from_file(files_controller_widget.selected_files[0])
    # Save config
    view.main_window.controller.preproc_config = get_preprocessing_config(view.controller)

    # Check if at least 2 oscillations of the lowest frequency band are present in the trials
    # Get the trial length depending on the segmentation type
    if segmentation.conditionRButton.isChecked():
        trl_len = segmentation.trialBox.value()
    else:
        trl_len = abs(segmentation.winBox_1.value()) + abs(segmentation.winBox_2.value())
    trl_len = trl_len/1000  # To seconds
    # Get the lowest frequency based on whether band segmentation is selected or not
    if not view.bandCBox.isChecked():
        min_freq = view.minbroadBox.value()
    else:
        selected_bands = view.selected_bands_by_type.get("segmentation", [])
        min_freq = min(band["min"] for band in selected_bands if band["name"] != 'broadband')
    # Throw a warning if there are not enough oscillations
    if (1/min_freq) > trl_len:
        QtWidgets.QMessageBox.warning(view, "Problematic band configuration",
                                      f"Your trial configuration does not allow even a single oscillation of the "
                                      f"lowest frequency. Consider increasing the trial duration or excluding the slower"
                                      f" frequencies.")

    # If band segmentation is selected, move the band selection to the RP
    if view.bandCBox.isChecked():
        text = view.bandLabel.text()
        view.main_window.stackedWidget.widget(idx + 2).controller.view.rpLabel.setText('Using bands from band segmentation step - ' + text)

    return True

