
def reset_all_controls(controller):
    """
    Hides all elements of the data preprocessing groupbox and resets them to defaults.
    Called at:
        - Analyzer startup
        - When 'Preprocess data' is unchecked
        - When files are deleted #TODO
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
        "fs": controller.main_window.sampling_frequency,
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
        "selected_files": controller.view.selected_files if controller.view.selected_files else None,
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