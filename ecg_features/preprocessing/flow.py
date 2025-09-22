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

# TODO HACER EL RESET DE HRV