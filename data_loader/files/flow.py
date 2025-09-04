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
    default_biosignal = view.biosignalBox.currentText()
    default_biosignal = default_biosignal.split(" ")[1]
    view.main_window.biosignal_info = view.controller.biosignals[default_biosignal]