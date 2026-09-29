from pathlib import Path
from typing import Dict, List, Union, Tuple, Callable
import json
import pandas as pd
import shutil
import time
from medusa_analyzer.backend.converter.prune_output import prune_output
from medusa.core.legacy.convert import _bids_label
from medusa.core import Recording
import mne
import numpy as np

SENSOR_NAMES = {'eeg': 'electrodes',
                'fnirs': 'optodes'}

def to_pascal_case(snake_str):
    """Convierte una cadena de snake_case a camelCase."""
    components = snake_str.split('_')
    return ''.join(x.title() for x in components)

def keys_to_pascal_case(data):
    """
    Recorre recursivamente diccionarios y listas para aplicar
    la conversión a camelCase exclusivamente a las claves.
    """
    if isinstance(data, dict):
        # Si es un diccionario, convierte la clave y llama recursivamente para el valor
        return {to_pascal_case(key): keys_to_pascal_case(value) for key, value in data.items()}
    elif isinstance(data, list):
        # Si es una lista, llama recursivamente sobre sus elementos por si contienen diccionarios
        return [keys_to_pascal_case(item) for item in data]
    else:
        # Caso base: devuelve el valor tal cual (int, float, str, booleanos)
        return data

def _remove_nulls(obj):
    if isinstance(obj, dict):
        return {k: _remove_nulls(v) for k, v in obj.items() if v is not None}
    elif isinstance(obj, list):
        return [_remove_nulls(item) for item in obj if item is not None]
    return obj

def _convert_medusa_to_mpl(data: Recording, output_path: Path):

    if not hasattr(data, "bids"):
        raise ValueError("The 'bids' key is missing from data.")

    # 1. Extracción de entidades BIDS
    subject = data.bids.subject
    session = data.bids.session
    task = data.bids.task
    acq = data.bids.acquisition
    run = data.bids.run

    entities = []
    entities.append(f"sub-{subject}")
    if session is not None: entities.append(f"ses-{session}")
    if task is not None: entities.append(f"task-{task}")
    if acq is not None: entities.append(f"acq-{acq}")
    if run is not None: entities.append(f"run-{run}")

    base_name = "_".join(entities)

    # Construcción de la ruta del sujeto y sesión (ej. dataset/sub-01/ses-01/)
    subject_output_path = output_path / f"sub-{subject}"
    if session is not None:
        subject_output_path = subject_output_path / f"ses-{session}"

    # Get experiment info
    experiment = keys_to_pascal_case(data.experiment)
    # experiment['TaskInformation'] = experiment

    # 2. Datos de Participant guardados en el participants.tsv raíz
    sociodemographics = data.bids.participant
    if sociodemographics is not None:
        sociodemographics_file = output_path / "participants.tsv"
        row = {"participant_id": f"sub-{subject}"}
        row.update(sociodemographics)
        df_part = pd.DataFrame([row])

        # Si el TSV existe, se añade la fila al final sin rescribir el encabezado
        if sociodemographics_file.exists():
            df_part.to_csv(sociodemographics_file, mode='a', sep='\t', index=False, header=False)
        else:
            df_part.to_csv(sociodemographics_file, sep='\t', index=False)

    # 3. Carpetas de data_type (eeg, emg, etc.) y Sidecars asociados
    for data_type, content in data.data.items():
        full_output_path = subject_output_path / data_type
        full_output_path.mkdir(parents=True, exist_ok=True)

        # Guardado de metadata tabular como electrodes, channels o sensors en formato TSV
        chann_data = content.channel_set
        for key_tsv in ['channels', 'sensors']:
            current_key = getattr(chann_data, key_tsv)
            if current_key:
                try:
                    df_tsv = pd.DataFrame([vars(channel) for channel in current_key]).fillna('n/a')
                except:
                    df_tsv = pd.DataFrame.from_dict({key: vars(sensor) for key, sensor in current_key.items()},orient='index').fillna('n/a')
                df_tsv = df_tsv.rename(columns={
                    'uid': 'name',
                    'ch_type': 'type',
                    'sensor_type': 'type',
                    'unit': 'units'
                })
                if key_tsv == 'sensors':
                    key_tsv = SENSOR_NAMES.get(data_type,'sensors')

                    df_tsv['x'] = df_tsv['coordinates'].str[0]
                    df_tsv['y'] = df_tsv['coordinates'].str[1]
                    df_tsv['z'] = df_tsv['coordinates'].str[2]

                    # 2. Eliminar la columna original
                    df_tsv = df_tsv.drop(columns=['coordinates'])

                df_tsv.to_csv(full_output_path / f"{base_name}_{key_tsv}.tsv", sep='\t', index=False)

        # Se genera el sidecar del datatype omitiendo el bloque pesado de la señal cruda
        sidecar = {k: v for k, v in data.sidecars[data_type].items()}
        if experiment is not None:
            sidecar.update(experiment)

        sidecar = _remove_nulls(sidecar)  # Eliminación de campos null
        with open(full_output_path / f"{base_name}_{data_type}.json", 'w', encoding='utf-8') as f:
            json.dump(sidecar, f, indent=4)

        # 3.5 Exportación de la señal cruda a formato EDF
        # Extracción de nombres de canales
        ch_names = [str(ch.label) for ch in content.channel_set.channels]
        # Estructuración del diccionario de salida
        signal_export = {
            "fs": content.fs,
            "channels": ch_names,
            "times": content.times.tolist(),
            "signal": content.signal.tolist()
        }

        # Se omite el parámetro 'indent' para evitar que el tamaño del archivo
        # crezca desproporcionadamente debido a la matriz de la señal.
        with open(full_output_path / f"{base_name}_{data_type}.mpl", 'w', encoding='utf-8') as f:
            json.dump(signal_export, f)

    # 4. Exportación de Eventos en TSV dentro de la misma jerarquía de la señal
    events = data.events
    if events and hasattr(events, 'df'):
        df_events = events.df
        # Export to TSV (BIDS uses 'n/a' for missing values)
        df_events.to_csv( subject_output_path / f"{base_name}_events.tsv", sep='\t', index=False, na_rep='n/a')

        # Generate and export JSON sidecar according to BIDS dictionary structure
        events_sidecar = {}
        for col_name, desc_text in events.descriptions.items():
            events_sidecar[to_pascal_case(col_name)] = desc_text
        events_sidecar = _remove_nulls(events_sidecar)  # Eliminación de campos null
        with open(subject_output_path / f"{base_name}_events.json", 'w', encoding='utf-8') as f:
            json.dump(events_sidecar, f, indent=4)


def _convert_mne_to_medusa(raw, *, task="rest", subject=None, session=None, run=None,
                  zero_time_origin=True, task_name=None):
    """Convert an MNE Raw object to a 2.0 :class:`Recording`.

    Mapping rules:
    - The channels are grouped by MNE channel type. Each type becomes a separate
      :class:`~medusa.core.data.signal.Signal` keyed by its type (e.g., 'eeg', 'ecg').
    - The MNE data arrays are transposed to `[n_samples, n_channels]`.
    - Channels are typed according to MNE channel types (mapped to BIDS equivalents).
    - `raw.annotations` are converted to an `Events` timeline (BIDS format).
    - Acquisition metadata is extracted from `raw.info`.

    Parameters
    ----------
    raw : mne.io.Raw
        The MNE Raw object to convert.
    task : str, optional
        BIDS ``task`` label for the new recording (default ``"rest"``).
    subject : str or None, optional
        Override the ``sub`` label. If ``None`` (default), attempts to extract it
        from `raw.info["subject_info"]`, falling back to ``"01"``.
    session : str or int or None, optional
        BIDS ``ses`` label.
    run : str or int or None, optional
        Optional BIDS ``run`` index.
    zero_time_origin : bool, optional
        Shift the time axis so the first recorded sample is ``t = 0`` and event onsets
        are relative to it (default ``True``). ``False`` keeps absolute timestamps.
    task_name : str or None, optional
        Human-readable ``TaskName`` written to every stream's sidecar. Defaults to
        ``task`` when ``None``.

    Returns
    -------
    medusa.core.data.recording.Recording
        The converted recording containing the signals, events, and MNE metadata.
    """
    from medusa.core.data import (Recording, BidsInfo, Signal, ChannelSet,
                                  Channel, BIDS_CHANNEL_TYPES)

    # -- Time origin and times --
    meas_date = raw.info.get("meas_date")
    abs_origin = meas_date.timestamp() if meas_date else 0.0

    if zero_time_origin:
        times = raw.times
    else:
        times = raw.times + abs_origin + (raw.first_samp / raw.info["sfreq"])

    # -- Events --
    events = _mne_annotations_to_events(raw, zero_time_origin, abs_origin)

    # -- Metadata --
    experiment = {
        "kind": "mne-raw",
        "time_origin": abs_origin,
        "source_metadata": {
            "sfreq": raw.info.get("sfreq"),
            "highpass": raw.info.get("highpass"),
            "lowpass": raw.info.get("lowpass"),
            "description": raw.info.get("description"),
            "subject_info": raw.info.get("subject_info")
        }
    }

    # -- Assemble the 2.0 Recording --
    sub_label = _bids_label(subject) or "01"
    ses_label = _bids_label(session, fallback=None) if session else None

    bids = BidsInfo(subject=sub_label, session=ses_label, task=task, run=run)
    rec = Recording(bids)

    # -- Signal extraction grouped by channel type --
    ch_types = np.array(raw.get_channel_types())
    unique_types = np.unique(ch_types)

    for ch_type in unique_types:
        idx = np.where(ch_types == ch_type)[0]
        type_ch_names = [raw.ch_names[i] for i in idx]

        # MNE returns [n_channels x n_samples], Medusa expects [n_samples x n_channels]
        type_data = raw.get_data(picks=type_ch_names).T

        channel_set = ChannelSet()
        if ch_type.lower() == 'eeg':
            channel_set.add_unipolar_eeg_channels(type_ch_names)
        else:
            bids_type = ch_type.upper()
            if bids_type not in BIDS_CHANNEL_TYPES:
                bids_type = "OTHER"
            channels = [Channel(name, ch_type=bids_type, unit="n/a") for name in type_ch_names]
            channel_set.add_channels(channels)

        signal = Signal(type_data, fs=float(raw.info["sfreq"]),
                        channel_set=channel_set, times=times)

        rec.add_signal(ch_type.lower(), signal)

    if events is not None:
        rec.set_events(events)

    rec.set_experiment(experiment)
    rec.set_sidecar(TaskName=task_name if task_name is not None else task)

    return rec


def _mne_annotations_to_events(raw, zero_time_origin, abs_origin):
    """Build the BIDS :class:`Events` timeline from MNE annotations."""
    from medusa.core.data import Events

    if not raw.annotations or len(raw.annotations) == 0:
        return None

    records = []
    first_time = raw.first_samp / raw.info["sfreq"]
    orig_time = raw.annotations.orig_time

    for annot in raw.annotations:
        onset = annot["onset"]

        # MNE onset logic: if orig_time is set, onsets are absolute.
        # Otherwise, they are relative to the start of the data file (first_time).
        if orig_time is not None:
            onset -= orig_time.timestamp()
            onset -= first_time
        else:
            onset -= first_time

        if not zero_time_origin:
            onset = onset + abs_origin + first_time

        records.append({
            "onset": float(onset),
            "duration": float(annot["duration"]),
            "trial_type": str(annot["description"]),
            "mark_type": "event" if float(annot["duration"]) == 0.0 else "condition"
        })

    if not records:
        return None

    records.sort(key=lambda r: r["onset"])

    descriptions = {
        "trial_type": {"Description": "Annotation description derived from MNE."},
        "mark_type": {"Description": "'event' (duration 0) or 'condition' (duration > 0)."}
    }

    events = Events(optional_columns={"trial_type": str, "mark_type": str},
                    descriptions=descriptions)
    events.append(records)

    return events


def file_to_bids(input_path: Path, output_path: Path):
    """
    Lee un archivo JSON estructurado y lo exporta en un formato compatible con BIDS.
    """

    if str(input_path).endswith(('.h5', '.rec.bson', '.rec.json')):
        data = Recording.load(str(input_path))
        _convert_medusa_to_mpl(data, output_path)
    else:
        data = mne.io.read_raw(str(input_path))
        data_mds = _convert_mne_to_medusa(data)
        _convert_medusa_to_mpl(data_mds, output_path)

def run_conversion(input_data: List[str], output_path: str, extensions: Tuple[str, ...] = ('.mat', '.h5py'),
                   progress_callback: Callable[[int], None] | None = None,
                   log_callback: Callable[[str, str], None] | None = None) -> None:
    """
    Ejecuta el proceso de conversión para la ruta especificada.

    Args:
        path: La ruta al directorio o archivo que se va a convertir.

    Returns:
        bool: Devuelve True si la conversión fue exitosa, False en caso contrario.
    """
    progress_callback(0)
    log_callback(f"MEDUSA file converter started", "")
    log_callback(f"Reading input data...", "")
    time.sleep(1)

    output_path = Path(output_path)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        error_msg = rf"Cannot create output folder: {e}."
        log_callback(error_msg, "error")
        raise Exception(error_msg)

    if not len(input_data) == 1 and Path(*input_data).is_dir():
        root_path = Path(*input_data)
        # Iterar de forma recursiva buscando solo archivos con las extensiones indicadas
        files = []
        for ext in extensions:
            files.extend(root_path.rglob(f"*{ext}"))

        if not files:
            # 4. Crear un mensaje de error más informativo
            extension_list_str = ", ".join([f"{ext}" for ext in extensions])
            error_msg = f"No files with the following extensions were found: {extension_list_str}."
            log_callback(error_msg, "error")
            raise Exception(error_msg)
    else:
        files = [Path(file) for file in input_data]
        root_path = files[0].parent

    # Gestión de dataset_description.json en la raíz del output
    dataset_desc_src = root_path / "dataset_description.json"
    # Se evalúa solo si no existe ya en el destino para evitar sobreescrituras en bucles
    try:
        if dataset_desc_src.exists():
            shutil.copy(dataset_desc_src, output_path / "dataset_description.json")
        else:
            default_dataset_desc = {
                "Name": output_path.name,
                "BIDSVersion": "MEDUSA-derived BIDS"
            }
            with open(output_path / "dataset_description.json", 'w', encoding='utf-8') as f:
                json.dump(default_dataset_desc, f, indent=4)
    except Exception as e:
        error_msg = f"Unable to create dataset_description.json. Verify permissions."
        log_callback(error_msg, "error")
        raise Exception(error_msg)

    progress_callback(5)
    log_callback(rf"Successfully read input data","")
    log_callback(rf"{len(files)} files detected","")
    log_callback(rf"Starting conversion...","")
    time.sleep(1)

    idx_callback = 90 / len(files)

    valid_files = files.copy()
    for file in files:
        try:
            file_to_bids(file, output_path)

            progress_callback(int(idx_callback * (files.index(file) + 1) - 0.5 * idx_callback + 5))
            log_callback(f"[{file.stem}] Successfully converted", "")
            time.sleep(1)
        except Exception as e:
            error_msg = f"[{file.stem}] Exception {e} during conversion"
            log_callback(error_msg, "error")
            valid_files.remove(file)

    progress_callback(95)
    log_callback(rf"Successfully converted {len(valid_files)} files","")
    log_callback(rf"Starting inheritance-based file pruning...","")
    time.sleep(1)

    try:
        prune_output(output_path)
    except Exception as e:
        error_msg = f"Exception during dataset inheritance-based file pruning: {e}"
        log_callback(error_msg, "error")
        raise Exception(error_msg)

    progress_callback(100)
    log_callback(rf"Inheritance-based file pruning successfully run","")
    log_callback(rf"Conversion completed: {len(valid_files)} of {len(files)} files converted successfully","")


    return