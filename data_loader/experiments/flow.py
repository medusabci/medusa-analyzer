import json

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
        view.main_window.experiment = experiment_data

    # Update total steps and progress bar in the main window
    view.main_window.total_steps = len(view.main_window.experiment['pipeline'])
    view.main_window.controller.set_progressbar()
    # Deactivate Next button
    view.main_window.nextButton.setDisabled(True)
