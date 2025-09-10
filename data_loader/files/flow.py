def get_files_config(controller):
    """
    Function that creates a dictionary with preprocessing configurations.
    """
    config = {
        "selected_files": controller.view.selected_files if controller.view.selected_files else None,
        "selected_biosignal": controller.view.biosignalBox.currentText().split(" ")[
            1] if controller.view.biosignalBox.currentText() else None
    }
    return config


def on_next_click(view):
    """
    Handles the event when the "Next" button is clicked. It loads the selected biosignal information
    """
    # Get the selected biosignal
    biosignal_txt = view.biosignalBox.currentText()
    biosignal = biosignal_txt.split(" ")[1]
    view.main_window.biosignal_info = view.controller.biosignals[biosignal]