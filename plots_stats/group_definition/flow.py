from PySide6 import QtWidgets

def on_next_click(view):

    # Check if any group name is empty
    for group in view.main_module.controller.groups:
        if not group.strip():
            QtWidgets.QMessageBox.warning(view, "Warning", "Group names cannot be empty.")
            return False

    return True
