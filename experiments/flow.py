import json

def on_next_clicked(controller):
    """
    Handles the event when the "Next" button is clicked. It loads the selected experiment configuration
    """
    # Get selected experiment
    checked_button = controller.button_group.checkedButton()
    experiment_id = checked_button.property("experiment_id")
    # Read the corresponding config file
    with open(experiment_id + "/config.json", "r") as f:
        experiment_data = json.load(f)

        # # Include the Data Loading
        # data_loader = {
        #     "step": "Data Loading",
        #     "path": "data_loader/controller",
        #     "widget": "DataLoaderrController"
        # }
        # # Insert at the beginning of the pipeline
        # experiment_data["pipeline"].insert(0, data_loader)

        controller.main_window.experiment = experiment_data

    # Update total steps and progress bar in the main window
    controller.main_window.total_steps = len(controller.main_window.experiment['pipeline'])
    controller.main_window.controller.set_progressbar()
