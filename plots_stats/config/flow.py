import json, importlib
from pathlib import Path
import re
import os


def get_config_config(controller):
    """
    Collects the current configuration from the UI.
    """
    # Configuration dict
    config = {
        "experiment_info": controller.experiment_info,
        "analysis_mode": "within" if controller.view.withinRButton.isChecked() else "between"
    }
    if controller.experiment_path:
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
    view.main_module.controller.config_config = get_config_config(view.controller)

    # Filter the recordings based on the selected criteria (e.g., within or between subjects)
    view.main_module.controller.subjects = get_subjects_from_list(view.main_module.controller.all_files)
    view.main_module.controller.recordings = get_recordings_from_list(view.main_module.controller.all_files)
    view.main_module.controller.params = get_params_from_list(view.main_module.controller.all_files)
    view.main_module.controller.bands = get_bands_from_list(view.main_module.controller.all_files)

    if not view.controller.loaded_widgets:

        # Loading screen
        view.main_module.loading.show()
        view.main_module.loading.set_progress(0, view.main_module)

        # Import the next module, based on the configuration
        # Read the JSON file
        with open("plots_stats/plot_stats_config.json", "r", encoding="utf-8") as f:
            modules_config = json.load(f)
            modules_config = modules_config['parameters']

        experiment = view.main_module.controller.config_config['experiment_info']['experiment_type']
        widgets = modules_config[experiment]


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

def get_subjects_from_list(recordings):
    """
    Extracts subject identifiers from a list of recording filenames.
    """
    sub_ids = [p for p in (Path(p).parts for p in recordings) for p in p if p.startswith("sub-") and not p.endswith(".mat")]

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

def get_params_from_list(recordings):
    """
    Extracts the parameter identifiers (values following '_param-') from a list of recording filenames.
    """
    params = []

    for f in recordings:
        match = re.search(r'_param-([^-_]+)', f) # Match '_param-' followed by any characters except '-' or '_'
        if match: # If a match is found, add the captured group (the parameter value) to the list
            params.append(match.group(1))

    # Remove duplicates and sort
    params = list(set(params))
    params.sort()

    return params


def get_bands_from_list(recordings):
    """
    Extracts the parameter identifiers (values following '_param-') from a list of recording filenames.
    """
    bands = []

    for f in recordings:
        match = re.search(r'_band-([^-_]+)', f) # Match '_param-' followed by any characters except '-' or '_'
        if match: # If a match is found, add the captured group (the parameter value) to the list
            bands.append(match.group(1))

    # Remove duplicates and sort
    bands = list(set(bands))
    bands.sort()

    return bands