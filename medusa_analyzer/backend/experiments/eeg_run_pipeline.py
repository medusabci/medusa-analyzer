import numpy as np
from scipy.stats import kurtosis, skew
import csv
from pathlib import Path
import json

from medusa.signal import frequency_filtering, spatial_filtering, artifact_removal, segmentation, transforms
from medusa.signal.metrics import *
import pandas as pd
import warnings
from typing import Callable


def run_eeg_feature_extraction(state,
                 progress_callback: Callable[[int], None] | None = None,
                 log_callback: Callable[[str, str], None] | None = None) -> None:
    """
    Main pipeline function of the eeg features extraction that executes preprocessing, segmentation, and parameter
    computation for all selected files based on the provided configuration.
    """

    # Get the selected files and associated variables
    selected_recordings = state['selected_recordings']
    total_files = len(selected_recordings)

    # To store rejection summary and execution logs
    rejection_summary = []
    execution_logs = []

    # Logs
    progress_callback(0)
    msg = f"MEDUSA EEG FEATURES EXTRACTION started"
    log_callback(msg, "")
    execution_logs.append(msg)
    msg = f"{total_files} files will be processed..."
    log_callback(msg, "")
    execution_logs.append(msg)

    # Store the bands if band segmentation is enabled, otherwise use broadband
    bands = state['preprocessing']['selected_frequency_bands']
    # Sorted bands to have broadband in the first position
    bands = sorted(bands, key=lambda b: 0 if b['id'].lower() == 'broadband' else 1)

    # Calculate total steps
    total_events = sum(
        len(group.get("duration_events", [])) + len(group.get("instant_events", []))
        for group in state["segmentation"]["event_groups"]
    )
    offset_event_a = 0.5
    offset_event_b = 2.5
    offset_band = 1
    offset_file = 1
    steps_per_event = offset_event_a + offset_event_b # Pasos dentro de un evento base
    steps_per_band = offset_band + (total_events * steps_per_event)  # Offset de banda + lo que ocupan sus condiciones
    steps_per_file = offset_file + (len(bands) * steps_per_band)  # Offset de archivo + lo que ocupan sus bandas
    total_steps = total_files * steps_per_file

    error_found = False

    # Loop through each selected file
    for idx_file, file in enumerate(selected_recordings):
        try:

            #0 Load data
            data = build_recording(file['path'], file['datatype'])
            datatype = file['datatype']
            subj_id = Path(file['path']).stem

            # Logs
            msg = f"Processing file {idx_file + 1}/{total_files}: {subj_id}"
            log_callback(msg,"")
            execution_logs.append(msg)

            # Get information from recording
            raw_signal = data.data[datatype].signal
            times = data.data[datatype].times
            fs = data.data[datatype].fs
            n_cha = data.data[datatype].channel_set.n_channels
            channs = data.data[datatype].channel_set.labels
            # Events
            base_name = Path(file['path']).name.rsplit('_', 1)[0]
            events_path = Path(file['path']).parent.parent /  f"{base_name}_events.tsv"
            events = pd.read_table(events_path)

            # Ensure consistent sampling frequency
            if fs != state['metadata']['sampling_frequency']:
                error_found = True
                msg = f"[{subj_id}] Does not have the sampling frequency of the selected pipeline."
                log_callback(msg, "error")
                execution_logs.append("[ERROR] " + msg)
                msg = f"[{subj_id}] Expected {state['metadata']['sampling_frequency']}, but got {fs}."
                log_callback(msg, "error")
                execution_logs.append("[ERROR] " + msg)
                continue

            # Logs
            msg = f"[{subj_id}] File loaded. Data successfully extracted"
            log_callback(msg, "")
            execution_logs.append(msg)

            ## First step: Preprocessing
            processed_signal = raw_signal.copy()
            if state['preprocessing']['car'] \
                    or any(filtro['enabled'] for filtro in state['preprocessing']['filters'].values()):
                processed_signal = apply_preprocessing(processed_signal, fs, state['preprocessing'])


            # Copy the data to avoid modifying the original data object
            save_outputs(
                build_output_dict(_convert(processed_signal), _convert(times), channs, fs),
                file, None, None, 'preprocessed', state
            )

            # Logs
            progress = int(((idx_file * steps_per_file) + offset_file) / total_steps * 100)
            progress_callback(progress)
            msg = f"[{subj_id}] File successfully preprocessed."
            log_callback(msg, "")
            execution_logs.append(msg)
            msg = f"[{subj_id}] Continuing with file processing..."
            log_callback(msg, "")
            execution_logs.append(msg)

            ## Second step: Get indices of the thresholding
            if state['segmentation']["thresholding"]['enabled']:



                epochs,_ = segment_signal(processed_signal, times, fs, events, state['segmentation'])

                # Get the thresholding parameters
                thres_k = state['segmentation']['thresholding']['sigma']
                thres_samples = state['segmentation']['thresholding']["samples"]
                thres_channels = state['segmentation']['thresholding']["channels"]
                idx_reject = dict()
                for base_evt, epochs_base in epochs.items():
                    idx_reject[base_evt] = {}
                    for evt, epochs_base_evt in epochs_base.items():
                        # Get the indices of rejected epochs
                        thres_mean = np.nanmean(np.nanmean(epochs_base_evt, axis=1), axis=0)
                        thres_std = np.nanmean(np.nanstd(epochs_base_evt, axis=1), axis=0)
                        prc_rejected, _, idx_reject[base_evt][evt] = artifact_removal.reject_noisy_segments(
                            epochs_base_evt, thres_mean, thres_std,
                            k=thres_k, n_samp=thres_samples, n_channels=thres_channels)

                        # Store rejection summary
                        prc_rejected = np.round(prc_rejected, 2)
                        n_rejected = int((prc_rejected * epochs[base_evt][evt].shape[0]) / 100)
                        rejection_summary.append({
                            'subject': subj_id,
                            'base_event': base_evt,
                            'event': evt,
                            'prc_rejected': prc_rejected,
                            'n_rejected': n_rejected
                        })

                del epochs, epochs_base, epochs_base_evt  # Free memory

            ## Third step: Band segmentation
            # For each band...
            for idx_band, band in enumerate(bands):
                # Band info
                band_name = band['id'].lower()
                low_cut, high_cut = band['low_cut'], band['high_cut']

                # Workaround to allow filtering in the Nyquist frequency
                if high_cut == fs/2:
                    high_cut -= 1e-6

                # If the band is not broadband, apply band filtering (the broadband does not require filtering)
                if band_name != 'broadband':
                    processed_signal_band = (frequency_filtering.FIRFilter(
                        state['preprocessing']['filters']['bandpass']['order'], [low_cut, high_cut],
                        'bandpass', window=state['preprocessing']['filters']['bandpass']['window'])
                                             .fit_transform(processed_signal.copy(), fs))
                else:
                    processed_signal_band = processed_signal.copy()

                ## Fourth step: Segmentation
                epochs, times_epochs = segment_signal(processed_signal_band, times, fs, events, state['segmentation'], log_callback, execution_logs, subj_id)

                evt_counter = 0
                for base_evt, epochs_base in epochs.items():
                    for evt, epochs_base_evt in epochs_base.items():
                        # Logs
                        evt_counter += 1
                        msg = f"[{subj_id}] Starting segmentation for event combination '{base_evt}' and '{evt}'..."
                        log_callback(msg, "")
                        execution_logs.append(msg)

                        ## Fifth step: Apply thresholding rejection if enabled
                        if state['segmentation']["thresholding"]['enabled']:
                            # If all the epochs are rejected, skip this condition
                            if np.all(idx_reject[base_evt][evt]):
                                # Logs
                                msg = f"[{subj_id}] All epochs corresponding to event combination '{base_evt}' and '{evt}' have been rejected. Skipping."
                                log_callback(msg, "warning")
                                execution_logs.append("[WARNING] " + msg)
                                continue

                            # Remove the rejected epochs from the epochs array
                            epochs[base_evt][evt] = np.delete(epochs[base_evt][evt], idx_reject[base_evt][evt], axis=0)

                        ## Sixth step: Apply resampling if enabled
                        current_fs = fs
                        current_times_epochs = times_epochs.copy()
                        if epochs[base_evt][evt] is not None and state['segmentation']['resampling']['enabled']:
                            resample_fs = state['segmentation']['resampling']['target_sampling_frequency']
                            time_start_ms = float(current_times_epochs[0]) if len(current_times_epochs) else 0.0
                            window = [time_start_ms, time_start_ms + (epochs[base_evt][evt].shape[1] / fs) * 1000]
                            epochs[base_evt][evt] = segmentation.resample_segments(
                                epochs[base_evt][evt], window, resample_fs)
                            current_fs = resample_fs

                            # Recalcular el vector de tiempos para que coincida con las nuevas dimensiones de las épocas
                            current_times_epochs = time_start_ms + (
                                np.arange(epochs[base_evt][evt].shape[1]) / current_fs) * 1000

                        # Logs
                        # progress = int((idx_file * steps_per_file) + offset_file + (idx_band * steps_per_band) + offset_band + (evt_counter * steps_per_event) + offset_event_a / total_steps * 100)
                        progress = int((((idx_file * steps_per_file) + offset_file + (
                                    idx_band * steps_per_band) + offset_band + ((
                                                                                            evt_counter - 1) * steps_per_event) + offset_event_a) / total_steps) * 100)
                        progress_callback(progress)
                        msg = f"[{subj_id}] Segmentation successfully computed for event combination '{base_evt}' and '{evt}' in band '{band_name}'."
                        log_callback(msg, "")
                        execution_logs.append(msg)
                        msg = f"[{subj_id}] Starting parameter computation..."
                        log_callback(msg, "")
                        execution_logs.append(msg)

                        # Save the segmented signals (if required), separately for each event
                        save_outputs(
                            build_output_dict(_convert(epochs[base_evt][evt]), _convert(current_times_epochs), channs,
                                current_fs, time_unit="ms"),
                            file, band_name, base_evt + evt, 'segmented', state
                        )

                        if n_cha == 1:
                            epochs[base_evt][evt] = epochs[base_evt][evt][:, :, None]

                        ## Seventh step: Parameter computation
                        params = compute_parameters(epochs[base_evt][evt], current_fs, band, state)
                        save_outputs(params, file, band_name, base_evt + evt, 'parameters', state)

                        # Logs
                        # progress = int((idx_file * steps_per_file) + offset_file + (idx_band * steps_per_band) + offset_band + (evt_counter * steps_per_event) + offset_event_a + offset_event_b / total_steps * 100)
                        progress = int((((idx_file * steps_per_file) + offset_file + (
                                    idx_band * steps_per_band) + offset_band + (
                                                     evt_counter * steps_per_event)) / total_steps) * 100)
                        progress_callback(progress)
                        msg = f"[{subj_id}] Parameters successfully computed for event combination '{base_evt}' and '{evt}' in band '{band_name}'."
                        log_callback(msg, "")
                        execution_logs.append(msg)

        # Exception handling
        except Exception as e:
            error_found = True
            msg = f"[{subj_id}] Error found during processing: {e}."
            log_callback(msg, "error")
            execution_logs.append("[ERROR] " + msg)
    # Save logs and summary
    try:
        msg = f"Saving logs..."
        log_callback(msg, "")
        execution_logs.append(msg)

        derivatives_path = Path(state['output_derivatives_path'])
        derivatives_path.mkdir(exist_ok=True)

        # Save rejection summary to CSV
        if rejection_summary:
            csv_path = get_unique_file_path(derivatives_path / "rejection_summary.csv")
            with open(csv_path, mode='w', newline='') as csv_file:
                fieldnames = ['subject', 'base_event', 'event', 'prc_rejected', 'n_rejected']
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()
                for row in rejection_summary:
                    writer.writerow(row)
                row = {
                    'subject': f"K STDs: {state['segmentation']['thresholding']['sigma']}",
                    'base_event': f"Samples: {state['segmentation']['thresholding']['samples']}",
                    'event': f"N Channels: {state['segmentation']['thresholding']['channels']}"
                }
                writer.writerow(row)
            msg = f"Rejection summary saved to {csv_path}."
            log_callback(msg, "")
            execution_logs.append(msg)

        # Save execution warnings/errors to TXT
        if execution_logs:
            log_path = get_unique_file_path(derivatives_path / "error_log.txt")
            with open(log_path, mode='w', encoding='utf-8') as txt_file:
                for log_entry in execution_logs:
                    txt_file.write(log_entry + "\n")
            msg = f"Execution logs saved to {log_path}."
            log_callback(msg, "")
            execution_logs.append(msg)

        msg = f"Logs successfully saved."
        log_callback(msg, "")
        execution_logs.append(msg)

    except Exception as e:
        msg = f"Error saving logs: {e}"
        log_callback(msg, "warning")
        execution_logs.append("[WARNING] " + msg)

    msg = f"MEDUSA EEG FEATURES EXTRACTION successfully finished"
    log_callback(msg, "")
    execution_logs.append(msg)
    progress_callback(100)

    if error_found:
        msg = f"Error(s) found during processing, please check logs"
        log_callback(msg, "warning")
        execution_logs.append("[WARNING] " + msg)

    return

#################### HELPER FUNCTIONS

def build_recording(path, datatype):
    from medusa.core.data import Recording, Signal, ChannelSet, BidsInfo

    with open(path) as json_data:
        data = json.load(json_data)

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=r".*not in montage.*", category=UserWarning)
        rec = Recording(BidsInfo(
            subject="dummy", session="dummy", task="dummy", run=1,
            participant={"age": 0, "sex": "F", "handedness": "right"}))
        cs = ChannelSet()
        cs.add_unipolar_eeg_channels(
            data['channels'],
            reference="DummyRef", ground="DummyGnd")
    sig = Signal(data['signal'],
                     fs=data['fs'], channel_set=cs)
    rec.add_signal(datatype, sig)

    return rec

def _convert(obj):
    if isinstance(obj, np.ndarray):
        return _convert(obj.tolist()) # Se añade recursividad
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: _convert(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert(v) for v in obj]
    return obj

def build_output_dict(signal, times, ch_names, fs, time_unit="s"):

    output_dic = {
        "fs": fs,
        "channels": ch_names,
        "times": times,
        "time_unit": time_unit,
        "signal": _convert(signal)
    }
    return output_dic

def _normalization_config(state):
    normalization = state.get('normalization') or {}
    if not isinstance(normalization, dict):
        raise ValueError("Segmentation normalization must be a dictionary with 'enabled' and 'mode'.")
    if 'duration' in normalization or 'instant' in normalization:
        raise ValueError("Segmentation normalization must not be stored per event type.")
    missing_keys = {'enabled', 'mode'} - set(normalization)
    if missing_keys:
        missing = ', '.join(sorted(missing_keys))
        raise ValueError(f"Segmentation normalization is missing required key(s): {missing}.")
    return normalization


def _resolve_event(events, evt):
    if isinstance(evt, dict):
        trial_type = evt['trial_type']
        response = evt['response']

        current_evts = events[
            (events['trial_type'] == trial_type) &
            (events['response'] == response)
        ]

        evt_name = f"{trial_type}_{response}"
    else:
        current_evts = events[events['trial_type'] == evt]
        evt_name = evt

    return current_evts, evt_name


def segment_signal(signal, times, fs, events, state,
                   log_callback = None, execution_logs = None, subj_id = None):

    # Get segmentation params, time vector and normalization type in a medusa-compatible format
    if state['segmentation_strategy'] == 'window-based':
        segment_length = state['epoch_parameters']['duration_events']['duration_epoch_length_ms']
        n_samples = int(np.round((segment_length / 1000.0) * fs))
        times_epochs_ms = (np.arange(n_samples) / fs) * 1000
        stride = state['epoch_parameters']['duration_events']['stride_percent']
        stride = None if stride == 0 else int((stride/100) * n_samples)

    else:
        epoch_window = [state['epoch_parameters']['instant_events']['start'],
                    state['epoch_parameters']['instant_events']['end']]
        baseline = [state['epoch_parameters']['instant_events']['baseline_start'],
                    state['epoch_parameters']['instant_events']['baseline_end']]
        segment_length = epoch_window[1] - epoch_window[0]
        n_samples = int(np.round((segment_length / 1000.0) * fs))
        # medusa_times_epochs = np.linspace(epoch_window[0], epoch_window[1], n_samples) / 1000
        times_epochs_ms = np.linspace(epoch_window[0], epoch_window[1], n_samples)

    normalization = _normalization_config(state)
    norm = None
    if normalization.get('enabled'):
        norm = 'z' if normalization.get('mode') == 'mean_std' else 'dc'
    else:
        baseline = None

    epochs = dict()
    for base_evt in state['event_groups']:
        if base_evt['base_event'] == None:
            base_evt['base_event'] = 'full_recording'
        epochs[base_evt['base_event']] = {}

        # Construcción del evento base
        if base_evt['base_event'] == 'full_recording':
            # Se crea un evento ficticio que abarca desde la primera muestra hasta el final.
            # Se añade un margen (+ 1.0 seg) para asegurar que searchsorted alcance el último índice.
            total_duration = times[-1] - times[0] + 1.0
            current_base_evt = pd.DataFrame([{'onset': times[0], 'duration': total_duration}])
        else:
            current_base_evt = events[events['trial_type'] == base_evt['base_event']]

        for row_base in current_base_evt.itertuples(index=False):
            start_idx = np.searchsorted(times, row_base.onset)
            end_idx = np.searchsorted(times, row_base.onset + row_base.duration)
            signal_base = signal[start_idx:end_idx, :]
            times_base = times[start_idx:end_idx]

            # If segmentation type is 'condition'
            all_events = base_evt['duration_events'] + base_evt['instant_events']
            for evt in all_events:
                current_evts, evt_name = _resolve_event(events, evt)

                if state['segmentation_strategy'] == 'window-based':

                    for row_evt in current_evts.itertuples(index=False):
                        start_idx = np.searchsorted(times_base, row_evt.onset)
                        end_idx = np.searchsorted(times_base, row_evt.onset + row_evt.duration)
                        # Validar que los índices están dentro del rango y forman un segmento válido
                        if start_idx >= len(times_base) or end_idx > len(times_base):
                            continue  # Ignorar esta iteración y pasar al siguiente evento

                        signal_evt = signal_base[start_idx:end_idx, :]

                        # Get epochs for the current condition
                        epochs_tmp = segmentation.segment_signal(
                            signal_evt, (segment_length/1000) * fs, stride, norm=norm)

                        if epochs_tmp is not None:
                            if evt in epochs[base_evt['base_event']]:
                                epochs[base_evt['base_event']][evt_name] = np.concatenate(
                                    (epochs[base_evt['base_event']][evt_name], epochs_tmp), axis=0)
                            else:
                                epochs[base_evt['base_event']][evt_name] = epochs_tmp
                            del epochs_tmp

                else:
                    try:
                        epochs_tmp = segmentation.segment_signal_around_events(
                            times_base*1000, signal_base, current_evts.onset*1000, fs,
                            [epoch_window[0], epoch_window[1]],
                            baseline,
                            norm=norm)
                    except KeyError:
                        continue

                    if epochs_tmp.size != 0:
                        epochs[base_evt['base_event']][evt_name]= epochs_tmp
                        del epochs_tmp
                    elif log_callback is not None:
                        msg = f"[{subj_id}] No epochs were found for event combination '{base_evt['base_event']}' and '{evt_name}'. Skipping."
                        log_callback(msg, "warning")
                        execution_logs.append("[WARNING] " + msg)

    return epochs, times_epochs_ms


def get_unique_file_path(path: Path) -> Path:
    """
    Comprueba si la ruta existe. Si es así, añade un sufijo _1, _2...
    antes de la extensión hasta encontrar un nombre disponible.
    """
    if not path.exists():
        return path

    counter = 1
    while True:
        new_path = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        if not new_path.exists():
            return new_path
        counter += 1


def save_outputs(data, file, band_name, evt, key, state):
    """
    Guarda los resultados del pipeline en estructura semi-BIDS dentro de /derivatives.

    Estructura:
    derivatives/
        ├── preprocessed/
        ├── segmented/
        └── parameters/
    """

    selected_folder = Path(state["output_derivatives_path"])
    selected_folder.mkdir(exist_ok=True)

    if evt is not None:
        evt = evt.replace('-', 'm').replace('_', '').replace('fullrecording','')

    # Obtener info del sujeto y sesión desde el nombre del archivo base
    filename = file['relative_path']
    # --- Saving preprocessed signals (.rec.bson) ---
    if key == "preprocessed":
        output_path = selected_folder / "preprocessed" / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

        # worker.log.emit(f"✅ Preprocessed saved: {output_path}", "")

    # --- Saving segmented signals (.json) ---
    elif key == "segmented":
        output_path = selected_folder / "segmented" / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        output_path = output_path.with_stem(f"{output_path.stem}_band-{band_name.replace('-', '')}_segment-{evt}")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

        # worker.log.emit(f"✅ Segmented saved: {output_path}", "")

    # --- Saving parameters ---
    elif key == "parameters":
        output_path_base = selected_folder / "parameters" / filename
        output_path_base.parent.mkdir(parents=True, exist_ok=True)

        params_dict = dict(data)

        # 1) Store PSDs only in broadband
        if band_name.lower() == 'broadband' and 'psd' in params_dict:
            output_path = output_path_base.with_stem(f"{output_path_base.stem}_param-psd"
                                                f"_band-{band_name.replace('-', '')}_segment-{evt}")

            save_struct = {
                'psd': np.asarray(params_dict['psd']['values']),
                'freqs': np.asarray(params_dict['psd']['freqs'])
            }

            output_dict = {'psd': _convert(save_struct)}
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_dict, f)

            # worker.log.emit(f"✅ Parameter saved: {outpath}", "")

        # 2) Other parameters
        for k, v in list(params_dict.items()):
            metric_label = k.replace('_', '-')

            output_path = output_path_base.with_stem(f"{output_path_base.stem}_param-{metric_label.replace('-', '')}"
                                                f"_band-{band_name.replace('-', '')}_segment-{evt}")

            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict) and 'band' in v[0]:
                for entry in v:
                    bname = entry.get('band', 'unknown')
                    val = np.asarray(entry.get('value'))

                    output_path = output_path_base.with_stem(f"{output_path_base.stem}_param-{metric_label.replace('-', '')}"
                                                        f"_band-{bname.replace('-', '')}_segment-{evt}")

                    output_dict = {"param": _convert(val), "info": metric_label}
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(output_dict, f)

                    # worker.log.emit(f"✅ Parameter saved: {output_path}", "")

            elif isinstance(v, dict):
                output_dict = {"param": _convert(v), "info": metric_label}
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(output_dict, f)

            else:
                output_dict = {"param": _convert(v), "info": metric_label}
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(output_dict, f)

            # worker.log.emit(f"✅ Parameter saved: {output_path}", "")


#################### PREPROCESSING

def apply_preprocessing(signal, fs, state):
    """
    Apply bandpass, notch filtering, and Common Average Reference (CAR).
    """
    # Bandpass filter
    for filter in state['filters'].values():
        if filter['enabled']:
            if filter['filter_design'] == 'fir':
                signal = frequency_filtering.FIRFilter(filter['order'], [filter['low_cut'], filter['high_cut']], filter['filter_type'],
                                          window=filter['window']).fit_transform(signal, fs)
            else:
                signal = frequency_filtering.IIRFilter(filter['order'], [filter['low_cut'], filter['high_cut']], filter['filter_type'],
                                          filt_method='sosfiltfilt').fit_transform(signal, fs)

    # CAR and return
    return spatial_filtering.car(signal) if state['car'] else signal

##################### COMPUTE PARAMS

def _feature_params(state, feature_id):
    params = state.get("feature_params", {})
    if not isinstance(params, dict):
        return {}
    feature_params = params.get(feature_id)
    return feature_params if isinstance(feature_params, dict) else {}


def _band_label(band):
    if not isinstance(band, dict):
        return ""
    label = str(band.get("id") or band.get("title") or "").strip()
    return label.lower().replace(" ", "_")


def compute_parameters(epochs, fs, band, state):
    # Initialize dict that will contain all the computed parameters
    params = {}
    selected_features = {str(feature) for feature in state.get('selected_features', [])}

    ## BASIC STATISTICAL PARAMETERS
    stat_funcs = {
        'mean': np.mean,
        'variance': np.var,
        'median': np.median,
        'kurtosis': kurtosis,
        'skewness': skew
    }
    # Account if only one (2D array) or multiple epoch are present (3D array)
    axis = 0 if epochs.ndim == 2 else 1
    # For each parameter...
    for name, func in stat_funcs.items():
        # If selected...
        if name in selected_features:
            # Compute it
            val = func(epochs, axis=axis)
            # Store in the params dict
            params[f"{name}"] = val

    ## POWER SPECTRAL DENSITY (PSD)
    # PSD is computed when it is selected or needed by another spectral metric.
    needs_psd = (
        'psd' in selected_features
        or "absolute_band_power" in selected_features
        or "relative_band_power" in selected_features
        or any(feature in selected_features for feature in ("median_frequency", "spectral_entropy"))
    )
    if needs_psd:
        # Use user-defined parameters for segmenting and windowing
        psd_params = _feature_params(state, "psd")
        segment_psd = float(psd_params.get('segment_percent', 80)) / 100
        overlap_psd = float(psd_params.get('overlap_percent', 50)) / 100
        window_psd = psd_params.get('window', 'hamming')

        # Compute PSD using specified segment and window settings
        fxx, psd = transforms.power_spectral_density(epochs, fs, segment_psd, overlap_psd, window_psd)

        # Store PSD values
        if 'psd' in selected_features:
            try:
                params['psd'] = {
                    'values': psd,
                    'freqs': fxx
                }
            except Exception as e:
                print(e)

    ## SPECTRAL METRICS - RELATIVE POWER
    if band['id'].lower() == 'broadband' and "relative_band_power" in selected_features:
        val = []

        # The bands will be different if band segmentation is enabled or not
        relative_band_power_params = _feature_params(state, "relative_band_power")
        selected_bands = relative_band_power_params.get('selected_frequency_bands', [])

        # Define broadband range based on the broadband limits
        min_val = band['low_cut']
        max_val = band['high_cut']

        # Loop through each selected band
        for band_rp in selected_bands:
            band_id = _band_label(band_rp)
            if band_id and band_id != 'broadband':
                # Define band parameters
                band_range = [band_rp["low_cut"], band_rp["high_cut"]]
                # Compute the metric
                val_band = spectral.band_power(psd, fs, band_range, 'relative',[min_val, max_val])
                val.append({"band": band_id, "value": val_band})

        if val:
            params["relative_band_power"] = val

    ## SPECTRAL METRICS - OTHERS
    spectral_funcs = {
        "absolute_band_power": spectral.band_power,
        "median_frequency": spectral.median_frequency,
        "spectral_entropy": nonlinear.shannon_spectral_entropy
    }

    # For each parameter...
    for name, func in spectral_funcs.items():
        # If selected...
        if name in selected_features:
            # Get the current band range
            band_range = [band['low_cut'], band['high_cut']]
            # Compute the metric
            if name == 'absolute_band_power':
                val = func(psd, fs, band_range, 'absolute')
            else:
                val = func(psd, fs, band_range)
            # Store in the params dict
            params[f"{name}"] = val

    ## NONLINEAR METRICS
    nonlinear_funcs = {
        'ctm': lambda: nonlinear.central_tendency_measure(epochs, state['feature_params']['ctm']['r']),
        'sample_entropy': lambda: nonlinear.sample_entropy(epochs,
                                                           state['feature_params']['sample_entropy']['m'],
                                                           state['feature_params']['sample_entropy']['r']),
        'multiscale_sample_entropy': lambda: nonlinear.multiscale_entropy(epochs,
                                                                          state['feature_params']['multiscale_sample_entropy']['max_scale'],
                                                                          state['feature_params']['multiscale_sample_entropy']['m'],
                                                                          state['feature_params']['multiscale_sample_entropy']['r']),
        'lzc': lambda: nonlinear.lempelziv_complexity(epochs),
        'multiscale_lzc': lambda: nonlinear.multiscale_lempelziv_complexity(epochs, state['feature_params']['multiscale_lzc']['scales'])
    }

    # For each parameter...
    for name, func in nonlinear_funcs.items():
        # If selected...
        if name in state['selected_features']:
            # Compute it
            val = func()
            params[f"{name}"] = val

    ## CONNECTIVITY METRICS
    connectivity_funcs = {
        'iac': lambda: connectivity.iac(epochs, state['feature_params']['iac']['orthogonalize']),
        'aec': lambda: connectivity.aec(epochs, state['feature_params']['aec']['orthogonalize']),
        'plv': lambda: connectivity.plv(epochs),
        'pli': lambda: connectivity.pli(epochs),
        'wpli': lambda: connectivity.wpli(epochs),
    }

    # For each parameter...
    for name, func in connectivity_funcs.items():
        # If selected...
        if name in state['selected_features']:
            # Compute it
            val = func()
            params[f"{name}"] = val

    return params