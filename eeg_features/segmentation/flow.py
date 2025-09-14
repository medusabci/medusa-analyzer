from PySide6.QtCore import QStringListModel
from PySide6 import QtWidgets


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
        "segmentation_type": "condition" if controller.view.conditionRButton.isChecked() else "event" if controller.view.eventRButton.isChecked() else None,

        "selected_conditions": selected_conditions,
        "selected_events": selected_events if controller.view.eventRButton.isChecked() else None,

        "trial_length": controller.view.trialBox.value() if controller.view.conditionRButton.isChecked() else None,
        "trial_stride": controller.view.trialstrideBox.value() if controller.view.conditionRButton.isChecked() else None,
        "window_start": controller.view.winBox_1.value() if controller.view.eventRButton.isChecked() else None,
        "window_end": controller.view.winBox_2.value() if controller.view.eventRButton.isChecked() else None,
        'norm': controller.view.normCBox.isChecked() if controller.view.normCBox else None,
        "norm_type": "z" if controller.view.normCBox.isChecked() and controller.view.zscoreRButton.isChecked() else
        "dc" if controller.view.normCBox.isChecked() and controller.view.dcRButton.isChecked() else None,
        "baseline_start": controller.view.baselineCBox_1.value() if controller.view.eventRButton.isChecked() and controller.view.normCBox.isChecked() else None,
        "baseline_end": controller.view.baselineCBox_2.value() if controller.view.eventRButton.isChecked() and controller.view.normCBox.isChecked() else None,
        'average': controller.view.averageCBox.isChecked() if controller.view.averageCBox else None,

        "thresholding": controller.view.thresCBox.isChecked() if controller.view.thresCBox else None,
        "thres_k": controller.view.threskBox.value() if controller.view.thresCBox.isChecked() else None,
        "thres_samples": controller.view.thressampBox.value() if controller.view.thresCBox.isChecked() else None,
        "thres_channels": controller.view.threschanBox.value() if controller.view.thresCBox.isChecked() else None,

        "resample": controller.view.resampleCBox.isChecked() if controller.view.resampleCBox else None,
        "resample_fs": controller.view.resamplefsBox.value() if controller.view.resampleCBox.isChecked() else None,
    }

    return config

def on_next_click(view):
    """
    """
    if not view.conditionRButton.isChecked() and not view.eventRButton.isChecked():
        QtWidgets.QMessageBox.warning(view, "Segmentation Selection Required", "Please select at least one segmentation type before proceeding.")
        return False

    if view.conditionRButton.isChecked() and not view.conditionList.selectionModel().selectedIndexes():
        QtWidgets.QMessageBox.warning(view,"Condition Selection Required", "Please select at least one condition before proceeding.")
        return False

    view.main_window.controller.segmentation_config = get_segmentation_config(view.controller)
    return True