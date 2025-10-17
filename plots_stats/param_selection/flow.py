from PySide6 import QtWidgets

def on_next_click(view):
    """
    Handles the event when the "Next" button is clicked
    """

    if not view.main_module.controller.data_assignment:
        QtWidgets.QMessageBox.warning(
            view,
            "Parameter Selection Error",
            f"Parameter selection failed. Please ensure that you have selected at least one parameter."
        )
        return False

    return True