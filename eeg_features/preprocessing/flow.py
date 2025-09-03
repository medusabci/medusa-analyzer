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

    # Disable grouped elements
    for elm in controller.view.element_group:
        elm.setDisabled(True)

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


def get_preprocessing_config(self):
    """
        Function that creates a dictionary with preprocessing configurations.
    """
    config = {
        "fs": self.main_window.sampling_frequency,
        "band_segmentation": True if self.view.bandCBox.isChecked() else None,
        "broadband_min": self.view.minbroadBox.value(),
        "broadband_max": self.view.maxbroadBox.value(),
        "selected_bands": (
            None
            if (not self.view.bandCBox.isChecked() or (
                    len(self.view.selected_bands_by_type.get("segmentation", [])) == 1 and
                    str(self.view.selected_bands_by_type.get("segmentation", [])[0].get("name",
                                                                                        "")).lower() == "broadband"
            ))
            else self.view.selected_bands_by_type.get("segmentation", [])
        ),
        "selected_files": self.view.selected_files if self.view.selected_files else None,
        "apply_preprocessing": True if self.view.preprocessingButton.isChecked() else None,

        "notch": self.view.notchCBox.isChecked() if self.view.notchCBox else None,
        "notch_min": self.view.minfreqnotchBox.value() if self.view.notchCBox.isChecked() else None,
        "notch_max": self.view.maxfreqnotchBox.value() if self.view.notchCBox.isChecked() else None,
        "notch_order": self.view.orderNotchBox.value() if self.view.notchCBox.isChecked() else None,
        "notch_win": self.view.winnotchBox.currentText() if self.view.notchCBox.isChecked() else None,

        "bandpass": self.view.bpCBox.isChecked() if self.view.bpCBox else None,
        "bp_min": self.view.minfreqbpBox.value() if self.view.bpCBox.isChecked() else None,
        "bp_max": self.view.maxfreqbpBox.value() if self.view.bpCBox.isChecked() else None,
        "bp_order": self.view.orderbpBox.value() if self.view.bpCBox.isChecked() else None,
        "bp_win": self.view.winbpBox.currentText() if self.view.bpCBox.isChecked() else None,

        "car": self.view.carCBox.isChecked() if self.view.carCBox else None,
    }
    return config