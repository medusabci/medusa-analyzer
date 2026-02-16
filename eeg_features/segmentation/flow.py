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

    if view.eventRButton.isChecked() and not view.eventList.selectionModel().selectedIndexes():
        QtWidgets.QMessageBox.warning(view,"Event Selection Required", "Please select at least one event before proceeding.")
        return False

    if view.eventRButton.isChecked() and view.eventList.selectionModel().selectedIndexes() and not view.conditionList.selectionModel().selectedIndexes():
        QtWidgets.QMessageBox.warning(view, "Condition Selection Required",
                                      "Please select at least one condition before proceeding. "
                                      "If no conditions are available, select 'no-condition'.")
        return False

    # Check if at least 2 oscillations of the lowest frequency band are present in the trials
    # Get the trial length depending on the segmentation type
    if view.conditionRButton.isChecked():
        trl_len = view.trialBox.value()
    else:
        trl_len = abs(view.winBox_1.value()) + abs(view.winBox_2.value())
    trl_len = trl_len/1000  # To seconds
    # Get the lowest frequency based on whether band segmentation is selected or not
    idx = view.main_window.stackedWidget.currentIndex()
    preprocessing = view.main_window.stackedWidget.widget(idx-1)
    if not preprocessing.bandCBox.isChecked():
        min_freq = preprocessing.minbroadBox.value()
    else:
        selected_bands = preprocessing.selected_bands_by_type.get("segmentation", [])
        min_freq = min(band["min"] for band in selected_bands if band["name"] != 'broadband')
    # Throw a warning if there are not enough oscillations
    if (1/min_freq) > trl_len:
        msg = QtWidgets.QMessageBox(view)
        msg.setIcon(QtWidgets.QMessageBox.Warning)
        msg.setWindowTitle("Problematic band configuration")
        msg.setText(
            "Your trial configuration does not allow even a single oscillation of the "
            "lowest frequency. Consider increasing the trial duration or excluding the slower "
            "frequencies. Do you want to proceed anyway?"
        )
        msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        msg.setDefaultButton(QtWidgets.QMessageBox.No)

        reply = msg.exec()
        if reply == QtWidgets.QMessageBox.No:
            return False

    view.main_window.controller.segmentation_config = get_segmentation_config(view.controller)
    return True