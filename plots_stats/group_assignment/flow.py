from PySide6 import QtWidgets

def on_next_click(view):
    """
    Handles the event when the "Next" button is clicked
    """
    view.main_module.controller.group_assignment = view.controller.group_assignment

    if len(view.main_module.controller.group_assignment) == 0:
        QtWidgets.QMessageBox.warning(
            view,
            "Group Assignment Error",
            "Group assignment data is missing. Please ensure that subjects have been assigned to groups."
        )
        return False


    # Check if any of the groups has no subjects assigned
    empty_groups = []
    for group, subjects in view.main_module.controller.group_assignment.items():
        if len(subjects) == 0:
            empty_groups.append(group)
    if empty_groups:
        QtWidgets.QMessageBox.warning(
            view,
            "Group Assignment Error",
            f"The group {', '.join([f'"{elem}"' for elem in empty_groups])} has no subjects assigned. Please, assign at least one subject to each group before proceeding, or reduce the number of groups."
        )
        return False

    return True