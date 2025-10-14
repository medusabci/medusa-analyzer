import json, importlib

def get_config_config(controller):
    """
    Collects the current configuration from the UI.
    """
    # Configuration dict
    config = {
        "experiment_info": controller.experiment_info,
        "selection": {
            "subject_mode": "within" if controller.view.withinRButton.isChecked() else "between",
            "data_type": "preprocessed" if controller.view.preprocessedRButton.isChecked() else "parameters"
        }
    }
    return config


def on_next_click(view):
    """
    Handles the event when the "Next" button is clicked
    """

    # return True  # For testing purposes, skip the rest of the function

    # Store the config
    view.main_module.controller.config_config = get_config_config(view.controller)

    if not view.controller.loaded_widgets:

        # Loading screen
        view.main_module.loading.show()
        view.main_module.loading.set_progress(0, view.main_module)



        # Import the next module, based on the configuration
        # Read the JSON fil
        with open("plots_and_stats/plot_stats_config.json", "r", encoding="utf-8") as f:
            modules_config = json.load(f)

        experiment = view.main_module.controller.config_config['experiment_info']['experiment_type']
        analysis = view.main_module.controller.config_config['selection']['data_type']
        widgets = modules_config[experiment][analysis]


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
            widget_controller_class(widget)

            # Add the widget to a stackedWidget
            view.main_module.stackedWidget.insertWidget(idx + 1, widget)

            # Update loading progress
            view.main_module.loading.set_progress(((idx + 1) / len(widgets)) * 100, view.main_module)

        # Finish loading
        view.main_module.loading.finish()

        view.controller.loaded_widgets = True

    return True
