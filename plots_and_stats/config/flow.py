import json, importlib
from pathlib import Path

def get_config_config(controller):
    """
    Collects the current configuration from the UI.
    """
    # Configuration dict
    config = {
        "experiment_info": controller.experiment_info,
        "selection": {
            "analysis_mode": "within" if controller.view.withinRButton.isChecked() else "between",
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

        if view.main_module.controller.config_config['selection']['data_type'] == 'parameters':
            view.main_module.controller.all_files = get_recordings_with_extension(view.main_module.controller.all_files,
                                                                                  '.mat')
        else:
            view.main_module.controller.all_files = get_recordings_with_extension(view.main_module.controller.all_files,
                                                                                  '.rec.bson')

        # Filter the recordings based on the selected criteria (e.g., within or between subjects)
        view.main_module.controller.subjects = get_subjects_from_list(view.main_module.controller.all_files)
        view.main_module.controller.recordings = get_recordings_from_list(view.main_module.controller.all_files)

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

def get_subjects_from_list(recordings):
    """
    Extracts subject identifiers from a list of recording filenames.
    """
    sub_ids = [p for p in (Path(p).parts for p in recordings) for p in p if p.startswith("sub-")]

    sub_ids = list(set(sub_ids))
    sub_ids.sort()

    return sub_ids

def get_recordings_from_list(recordings):
    """
    Extracts subject identifiers from a list of recording filenames.
    """
    keys_to_remove = ["sub", "ses", "param","band"]

    clean_recordings = []
    for f in recordings:
        p = Path(f)
        stem = p.stem  # Name without extension
        parts = stem.split("_")  # Separate by underscores (assuming BIDS-like structure)
        # Remove parts that start with any of the keys to remove followed by a hyphen
        new_parts = [part for part in parts if not any(part.startswith(k + "-") for k in keys_to_remove)]
        clean_name = "_".join(new_parts) # Add the rest of the parts back together
        clean_recordings.append(clean_name)

    clean_recordings = list(set(clean_recordings))
    clean_recordings.sort()

    return clean_recordings


def get_recordings_with_extension(recordings, extension):
    """
    Given a list of recording names without extensions, find the corresponding files with extensions.
    """
    filtered_recordings = [p for p in recordings if p.endswith(extension)]

    return filtered_recordings

