# plots/config/flow.py
import os
import json

def load_widget_config(config_path):
    """Carga la configuración del flujo de widgets."""
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load widget config: {e}")
    return {}

def validate_experiment_path(path):
    """Valida el directorio del experimento y devuelve mensajes + info."""
    if not os.path.exists(path):
        return {
            "message": "⚠️ Path does not exist.",
            "expinfo": "",
            "experiment_info": None
        }

    settings_file = os.path.join(path, "settings.json")
    if not os.path.isfile(settings_file):
        return {
            "message": "⚠️ settings.json not found in this directory.",
            "expinfo": "",
            "experiment_info": None
        }

    try:
        with open(settings_file, "r") as f:
            data = json.load(f)
        exp_type = data.get("experiment_type", "Unknown")
        signal_type = data.get("files", {}).get("selected_biosignal", "Unknown").upper()
        return {
            "message": "",
            "expinfo": f"✅ Detected Experiment: {exp_type} ({signal_type})",
            "experiment_info": {"experiment_type": exp_type, "signal_type": signal_type}
        }
    except Exception as e:
        return {
            "message": f"⚠️ Error reading settings.json: {e}",
            "expinfo": "",
            "experiment_info": None
        }

def is_next_enabled(experiment_info, between_checked, within_checked, preproc_checked, params_checked):
    """Evalúa si el botón Next debe habilitarse."""
    return (
        experiment_info
        and (between_checked or within_checked)
        and (preproc_checked or params_checked)
    )

def build_next_config(experiment_path, experiment_info, between_checked, preproc_checked, widget_config):
    """Construye el diccionario que se emite al siguiente paso."""
    analysis_type = "between" if between_checked else "within"
    data_type = "preprocessed" if preproc_checked else "parameters"

    exp_type = experiment_info.get("experiment_type") if experiment_info else None
    widget_sequence = widget_config.get(exp_type, {}).get(data_type, []) if exp_type else []

    return {
        "experiment_path": experiment_path,
        "experiment_info": experiment_info,
        "analysis_type": analysis_type,
        "data_type": data_type,
        "widget_sequence": widget_sequence,
    }
