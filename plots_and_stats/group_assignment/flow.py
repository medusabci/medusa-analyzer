from PySide6 import QtWidgets

def on_next_click(view):
    """
    Handles the event when the "Next" button is clicked
    """

    # Check if any of the groups has no subjects assigned
    for group, subjects in view.main_module.controller.group_assignment.items():
        if len(subjects) == 0:
            QtWidgets.QMessageBox.warning(
                view,
                "Group Assignment Error",
                f"The group '{group}' has no subjects assigned. Please, assign at least one subject to each group before proceeding, or reduce the number of groups."
            )
            return False

    return True