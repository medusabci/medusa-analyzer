from __future__ import annotations

from math import isfinite
from pathlib import Path
from typing import Any, Callable

from medusa_analyzer.frontend.validation.bids_validator import validate_bids_dataset

"""Scripys que carga un dataset BIDS de EEG, usa el validador geenral para encontrar registros raw en la BBDD, 
y luego los agrupa por configuración común: tarea, frecuencia de muestreo, referencia, canales, eventos, etc."""

# TODO: las deafault_raw_extensions tienen que ir al defaults.json
DEFAULT_RAW_EXTENSIONS = [".edf", ".vhdr", ".vmrk", ".eeg", ".set", ".fdt", ".bdf", ".mpl"]
NULL_RESPONSE_VALUES = {"", "n/a", "na", "nan", "none", "null"}


def _response_value(value: Any) -> Any | None:
    if value is None:
        return None

    text = str(value).strip()
    if text.lower() in NULL_RESPONSE_VALUES:
        return None

    numeric_text = text.replace(",", ".")
    try:
        number = float(numeric_text)
    except ValueError:
        return text

    if not isfinite(number):
        return None
    if number.is_integer():
        return int(number)
    return number


def _add_response(event_responses: dict[str, list[Any]], event_name: str, response: Any) -> None:
    responses = event_responses.setdefault(event_name, [])
    if response not in responses:
        responses.append(response)


def load_eeg_bids_dataset(root: str | Path, config: dict[str, Any] | None = None,
    progress_callback: Callable[[int], None] | None = None,
    log_callback: Callable[[str, str], None] | None = None) -> dict[str, Any]:
    """

    :param root: carpeta raíz del dataset BIDS
    :param config: configuración opcional
    :param progress_callback: función opcional para indicar progreso
    :param log_callback: función opcional para registrar mensajes
    :return: diccionario con los grupos de registros EEG encontrados
    """
    config = dict(config or {})
    allowed_datatypes = [str(item).lower() for item in config.get("allowed_datatypes", ["eeg"])]
   # TODO: NOTA; No viene en el json de defaults. Por defecto usa lo mismo que allowed_datatypes.
    # TODO: Igual quitar esto?? Que no sea necesario acceder a la config??
    # Descarta de channels.tsv las filas que no sean de un tipo compatible con nuestra señal
    allowed_signal_types = {str(item).upper() for item in config.get("allowed_signal_types", allowed_datatypes)}
    if log_callback:
        log_callback("Checking EEG-compatible BIDS recordings.", "info")
    # Llamamos al validador general de BIDS
    inventory = validate_bids_dataset(root, allowed_datatypes=allowed_datatypes,
        raw_extensions=config.get("raw_extensions", DEFAULT_RAW_EXTENSIONS),
        progress_callback=progress_callback, log_callback=log_callback)

    if inventory["errors"]:
        raise ValueError("\n".join(inventory["errors"][:8]))

    warnings = list(inventory["warnings"])

    groups: dict[tuple[Any, ...], dict[str, Any]] = {} # dic para agrupar los registros
    # Iteramos sobre todos los registros encontrados
    for recording in inventory["recordings"]:
        metadata = recording["metadata"] # Obtenemos lso metadatos
        try:
            sampling_frequency = float(metadata["SamplingFrequency"])
        except (KeyError, TypeError, ValueError):
            warnings.append(f"Skipping {recording['relative_path']}: missing or invalid SamplingFrequency.")
            continue

        channels = recording["tables"].get("channels") or [] # Obtenemos la tabla de channels
        # Filtramos las filas de la tabla de los canales para quedarnos solo con canales del tipo de nuestra señal
        signal_rows = [row for row in channels
            if str(row.get("type", "")).strip().upper() in allowed_signal_types]
        if not signal_rows:
            warnings.append(f"Skipping {recording['relative_path']}: no compatible channels.tsv rows.")
            continue

        entities = recording["entities"] # obtenemos entidades BIDS del nombre del archivo
        # Obtenemos información de la tarea
        task_info = metadata.get("TaskInformation") if isinstance(metadata.get("TaskInformation"), dict) else {}
        task_nested = next((value for value in task_info.values() if isinstance(value, dict)), {})
        task = entities.get("task") or metadata.get("TaskName") or task_info.get("TaskName") or task_info.get("Taskname")
        task = task or task_nested.get("TaskName") or task_nested.get("Taskname") or "n/a"
        # Obtenemos información de los canales
        channel_names = tuple(str(row.get("label", "")).strip() for row in signal_rows if row.get("label"))
        channel_types = tuple(str(row.get("type", "")).strip().upper() for row in signal_rows if row.get("label"))
        reference = str(metadata.get("EEGReference") or "n/a")
        # Obtenemos información de los eventos
        events = recording["tables"].get("events") or []
        # Si hay eventos, guardamos los nombres de las columnas del primer evento (asumimos que todos tienen las mismas columnas)
        event_columns = tuple(events[0].keys()) if events else ()
        # Creamos dos conjuntos de eventos
        duration_events: set[str] = set()
        instant_events: set[str] = set()
        event_responses: dict[str, list[Any]] = {}
        for row in events:
            event_name = str(row.get("trial_type") or "").strip()
            if not event_name:
                continue
            if "response" in row:
                response = _response_value(row.get("response"))
                if response is not None:
                    _add_response(event_responses, event_name, response)
            try:
                duration = float(str(row.get("duration") or "0").replace(",", "."))
            except ValueError:
                duration = 0.0
            if duration >= 1.0:
                duration_events.add(event_name)
            else:
                instant_events.add(event_name)
        # Añadimos el evento 'full_recording'. Siempre lo ponemos primero
        duration_events.add("full_recording")
        # Creamos listas ordenadas de los tipos de evento
        duration_event_types = tuple(["full_recording"] + sorted(duration_events - {"full_recording"}))
        instant_event_types = tuple(sorted(instant_events))
        event_types = tuple(sorted(duration_events | instant_events)) # Lista con todos los tipos de evento

        # Creamos una clave única para agrupar registros con la misma configuración
        key = (recording["datatype"], task, sampling_frequency, reference, channel_names, channel_types,
            event_columns, duration_event_types, instant_event_types)
        # Dos registros estarán en el mismo grupo si coinciden en datatype, tarea, fs, referencia, nombres
        # canales, tipos de canales, columnas de eventos, eventos de duración y eventos instantáneos.

        # Buscamos si ya existe un grupo con esa clave. Si existe la usa y si no crea una nueva.
        group = groups.setdefault(key, {
            "datatype": recording["datatype"],
            "task": task,
            "sampling_frequency": sampling_frequency,
            "reference": reference,
            "channel_set": list(channel_names),
            "event_columns": list(event_columns),
            "event_types": list(event_types),
            "duration_events": list(duration_event_types),
            "instant_events": list(instant_event_types),
            "event_responses": {},
            "raw_extensions": set(),
            "recordings": [],
        })

        for event_name, responses in event_responses.items():
            for response in responses:
                _add_response(group["event_responses"], event_name, response)

        group["raw_extensions"].add(recording["extension"])
        group["recordings"].append({
            "path": recording["path"],
            "relative_path": recording["relative_path"],
            "subject": entities.get("sub"),
            "session": entities.get("ses"),
            "run": entities.get("run"),
            "datatype": recording["datatype"],
            "extension": recording["extension"],
            "json_sidecars": recording["json_sidecars"],
            "sidecars": recording["sidecars"],
        })

    if not groups:
        detail = "\n".join(warnings[:8])
        raise ValueError(f"No EEG-compatible BIDS recordings found.\n{detail}".strip())

# Convierte los grupos en lista y los ordena de mayor a menor número de grabaciones.
    group_list = sorted(groups.values(), key=lambda group: len(group["recordings"]), reverse=True)
    for index, group in enumerate(group_list, start=1):
        recordings = group["recordings"] # guardamos la lista de grabaciones del grupo
        group["id"] = f"group-{index}"
        group["n_recordings"] = len(recordings)
        group["subjects"] = sorted({item["subject"] for item in recordings if item.get("subject")})
        group["sessions"] = sorted({item["session"] for item in recordings if item.get("session")})
        group["n_channels"] = len(group["channel_set"])
        group["raw_extensions"] = sorted(group["raw_extensions"])

    if len(group_list) > 1:
        warnings.append(f"Detected {len(group_list)} different BIDS recording configuration(s).")
    if log_callback:
        for warning in warnings:
            log_callback(warning, "warning")

    return {"root": inventory["root"], "groups": group_list, "warnings": warnings}


__all__ = ["load_eeg_bids_dataset"]
