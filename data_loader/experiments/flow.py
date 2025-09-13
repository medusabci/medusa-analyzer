import json, importlib

def on_next_click(view):
    """
    Handles the event when the "Next" button is clicked. It loads the selected experiment configuration
    """
    # Get selected experiment
    checked_button = view.button_group.checkedButton()
    experiment_id = checked_button.property("experiment_id")

    # Read the corresponding config file
    with open(experiment_id + "/config.json", "r") as f:
        experiment_data = json.load(f)
        view.controller.experiment = experiment_data

    # Load the widgets, instantiate their controllers and add them to the stackedWidget
    for idx,widget_info in enumerate(view.controller.experiment['pipeline']):
        # Take the path
        widget_path = widget_info['path'].replace('/','.') # use dots instead of slashes

        # Import the view
        ui_module = importlib.import_module(f"{widget_path}.ui")
        # Import the controller
        ctrl_module = importlib.import_module(f"{widget_path}.controller")

        # Get the classes from the modules
        widget_class = getattr(ui_module, widget_info['widget'])
        widget_controller_class = getattr(ctrl_module, widget_info['controller'])

        # Instantiate the widget
        widget = widget_class(view.main_window)
        # Instantiate the controller, passing the widget and the main window
        widget_controller_class(widget)

        # Optionally, add the widget to a stackedWidget
        view.main_window.stackedWidget.insertWidget(idx+1, widget)

    # Update total steps and progress bar in the main window
    view.main_window.total_steps = len(view.controller.experiment['pipeline'])
    view.main_window.controller.set_progressbar()
    # Deactivate Next button
    view.main_window.nextButton.setDisabled(True)

    return True