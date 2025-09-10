from PySide6.QtCore import QStringListModel
from PySide6 import QtWidgets

def on_next_click(view):
    """
    """
    if not view.conditionRButton.isChecked() and not view.eventRButton.isChecked():
        QtWidgets.QMessageBox.warning(view, "Segmentation Selection Required", "Please select at least one segmentation type before proceeding.")
        return False

    if view.conditionRButton.isChecked() and not view.conditionList.selectionModel().selectedIndexes():
        QtWidgets.QMessageBox.warning(view,"Condition Selection Required", "Please select at least one condition before proceeding.")
        return False

    return True