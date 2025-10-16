def get_files_config(controller):
    """
    Function that creates a dictionary with preprocessing configurations.
    """
    config = {
        "selected_files": controller.selected_files if controller.selected_files else None,
        "selected_biosignal": controller.view.biosignalBox.currentText().split(" ")[
            1] if controller.view.biosignalBox.currentText() else None,
        "selected_class":controller.view.biosignalBox.currentText().split(" ")[
            -1] if controller.view.biosignalBox.currentText() else None,
        "channel_names": controller.channels
    }
    return config


def on_next_click(view):
    """
    Handles the event when the "Next" button is clicked. It loads the selected biosignal information
    """
    # Get the selected biosignal
    biosignal_txt = view.biosignalBox.currentText()
    biosignal = biosignal_txt.split(" ")[1]
    view.controller.biosignal_info = view.controller.biosignals[biosignal]
    view.main_window.controller.files_config = get_files_config(view.controller)

    return True