from PySide6 import QtWidgets

def get_step_1_config(controller):
    """
    Function that creates a dictionary with step_1 configurations.
    """
    config = {
        "box1": controller.view.box1.value() if controller.view.do_box1.isChecked() else None,
        "box2": controller.view.box2.value() if controller.view.do_box2.isChecked() else None,
        "some_text1": controller.view.text1.value(),
        "some_text2": controller.view.text2.value()
    }
    return config

def on_next_click(view):
    """
    Handles the event when the "Next" button is clicked.
    """

    # If something is wrong, show an error message and return
    if view.box_1.value() > view.box_2.value():
        QtWidgets.QMessageBox.critical(view, "Error", "Box 1 value cannot be greater than Box 2 value.")
        return False

    # Save config
    view.main_window.controller.preproc_config = get_step_1_config(view.controller)

    return True

