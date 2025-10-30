from PySide6 import QtWidgets

def on_next_click(view):
    """
    Handles the event when the "Next" button is clicked
    """

    view.main_module.controller.data_assignment = view.controller.data_assignment

    if not view.main_module.controller.data_assignment:
        QtWidgets.QMessageBox.warning(
            view,
            "Data Assignment Error",
            f"Data assignment failed. Please ensure that you have selected at least one element."
        )
        return False

    return True