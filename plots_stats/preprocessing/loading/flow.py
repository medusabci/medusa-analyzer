import json, importlib
from pathlib import Path
import re
import os


def get_preproc_plot_config(controller):
    """
    Collects the current configuration from the UI.
    """
    # Configuration dict
    config = {
    }
    if controller.preprocessing_path and controller.experiment_path:
        settings_path = os.path.join(controller.experiment_path, "settings.json")
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        config["channel_names"] = data.get("files", {}).get("channel_names", [])
    else:
        config["channel_names"] = []

    return config


def on_next_click(view):
    """
    Handles the event when the "Next" button is clicked
    """
    # Store the config
    view.main_module.controller.preproc_plot_config = get_preproc_plot_config(view.controller)
    if not view.controller.loaded_widgets:

        # Loading screen
        view.main_module.loading.show()
        view.main_module.loading.set_progress(0, view.main_module)

        # Import the next module, based on the configuration
        # Read the JSON file
        with open("plots_stats/plot_stats_config.json", "r", encoding="utf-8") as f:
            modules_config = json.load(f)
            widgets = modules_config['preprocess']

        # Load the widgets, instantiate their controllers and add them to the stackedWidget
        for idx, widget_info in enumerate(widgets):
            # Take the path
            widget_path = widget_info['path'].replace('/', '.')  # use dots instead of slashes

            # Import the view
            ui_module = importlib.import_module(f"{widget_path}.view")
            # Import the controller
            ctrl_module = importlib.import_module(f"{widget_path}.controller")

            # Get the classes from the modules
            widget_class = getattr(ui_module, widget_info['widget'])
            widget_controller_class = getattr(ctrl_module, widget_info['controller'])

            # Instantiate the widget
            widget = widget_class(view.main_module)
            # Instantiate the controller, passing the widget and the main window
            controller_instance = widget_controller_class(widget)
            widget.controller = controller_instance
            print(
                f"DEBUG Creado controller {controller_instance} para widget {widget_info['widget']} id(view)={id(widget)}")

            # Add the widget to a stackedWidget
            view.main_module.stackedWidget.insertWidget(idx + 1, widget)

            # Update loading progress
            view.main_module.loading.set_progress(((idx + 1) / len(widgets)) * 100, view.main_module)

        # Finish loading
        view.main_module.loading.finish()

        view.controller.loaded_widgets = True

    return True
