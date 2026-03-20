from PySide6 import QtWidgets
from PySide6.QtCore import QThread, Signal
import medusa
import medusa.artifact_removal
import medusa.transforms
from medusa.signal_metrics import band_power, median_frequency, shannon_spectral_entropy, central_tendency
from medusa.signal_metrics import sample_entropy, multiscale_entropy, multiscale_lempelziv_complexity, \
    lempelziv_complexity
from medusa.connectivity_metrics import iac, aec, plv, pli, wpli
import numpy as np
from os.path import basename, join, splitext
from os import makedirs
from copy import deepcopy

from scipy.stats import kurtosis, skew
from scipy.io import savemat
import re
import json
import csv
from pathlib import Path


# Worker class to run the pipeline in a separate thread
class PipelineWorker(QThread):
    # Emit when the processing is finished
    finished = Signal(bool)
    # For updating the progress bar in the GUI
    progress = Signal(int)
    # For updating text progress in the GUI
    text_progress = Signal(str)
    # For updating log messages in the GUI
    log = Signal(str,str)

    def __init__(self, settings_dic):
        super().__init__()
        self.settings_dic = settings_dic

    def run(self):
        """Runs run_pipeline in a separate thread and emits finished signal when done."""
        try:
            # Call the main pipeline function
            error_found = self.run_pipeline(self.settings_dic)
        except Exception as e: # if error
            self.log.emit(f"Error in pipeline: {e}","error")
            error_found = True
        self.finished.emit(error_found)


    def run_pipeline(self, settings_dic):
        """
        Main pipeline function of the eeg features extraction that executes preprocessing, segmentation, and parameter
        computation for all selected files based on the provided configuration.
        """

        # Get the selected files and associated variables
        selected_files = settings_dic['files'].get('selected_files', [])
        total_files = len(selected_files)
        error_found = False

        # Store the bands if band segmentation is enabled, otherwise use broadband
        bands = settings_dic['preprocessing']['selected_bands'] if (
            settings_dic['preprocessing']['band_segmentation']) else [
            {'name': 'broadband', 'min': settings_dic['preprocessing']['broadband_min'],
             'max': settings_dic['preprocessing']['broadband_max']}]

        # Sorted bands to have broadband in the first position
        bands = sorted(bands, key=lambda b: 0 if b['name'].lower() == 'broadband' else 1)

        # Config of the progress bar
        steps_per_cond = 7
        steps_per_band = 1 + steps_per_cond * len(settings_dic['segmentation']['selected_conditions'])
        steps_per_file = 3 + steps_per_band * len(bands)
        total_steps = total_files * steps_per_file # Total steps for the progress bar

        # To store rejection summary and execution logs
        rejection_summary = []
        execution_logs = []

        def _log_with_store(msg, level):
            self.log.emit(msg, level)
            if level in ['warning', 'error']:
                execution_logs.append(f"[{level.upper()}] {msg}")

        # Loop through each selected file
        for i, file in enumerate(selected_files):
            try:
                # Logging and GUI updates
                self.log.emit(f"Processing file: {file}", "")
                self.text_progress.emit(f"Processing: {basename(file)}")

                # Load data
                base_name = splitext(basename(file))[0]
                data = medusa.components.Recording.load(file)
                # Initialize variables
                name_signal = settings_dic['files']['selected_biosignal']  # ej: "eeg"
                original_signal = getattr(data, name_signal).signal
                signal_times = getattr(data, name_signal).times
                signal_marks = include_no_conditions_in_marks(data.marks, signal_times)
                fs = getattr(data, name_signal).fs
                n_cha = getattr(data, name_signal).channel_set.n_cha

                # Update the progress bar and labels
                global_progress = (i*steps_per_file + 1) / total_steps * 100
                self.progress.emit(int(global_progress))

                # Ensure consistent sampling frequency
                if fs != settings_dic['preprocessing']['fs']:
                    raise Exception("One of the selected signals do not have the same sampling frequency: " + file)

                ## First step: Preprocessing
                processed_signal = deepcopy(original_signal)
                if settings_dic['preprocessing']['apply_preprocessing']:
                    processed_signal = apply_preprocessing(processed_signal, fs, settings_dic['preprocessing'])

                # Update the progress bar and labels
                global_progress = (i*steps_per_file + 2) / total_steps * 100
                self.progress.emit(int(global_progress))

                ## Second step: Get indices of the thresholding
                if settings_dic['segmentation']["thresholding"]:

                    # Get the thresholding parameters
                    thres_k = settings_dic['segmentation']['thres_k']
                    thres_samples = settings_dic['segmentation']["thres_samples"]
                    thres_channels = settings_dic['segmentation']["thres_channels"]
                    # Dict containing the indices of rejected epochs for each condition
                    idx_threshold = dict()

                    # For each condition selected...
                    for cond in settings_dic['segmentation']['selected_conditions']:

                        # If segmentation type is 'condition'
                        if settings_dic['segmentation']['segmentation_type'] == 'condition':
                            # Get epochs for the current condition
                            epochs = get_epochs_from_condition(
                                processed_signal, cond, signal_marks, signal_times, fs, settings_dic['segmentation'])

                        elif settings_dic['segmentation']['segmentation_type'] == 'event':
                            # Get all the selected events for this condition
                            epochs = []
                            for evt in settings_dic['segmentation']['selected_events']:
                                try:
                                    epochs_tmp = get_epochs_from_condition(
                                        processed_signal, cond, signal_marks, signal_times, fs, settings_dic['segmentation'],
                                        event=evt)
                                except KeyError:
                                    continue
                                if epochs_tmp is not None:
                                    epochs.append(epochs_tmp)
                                    del epochs_tmp

                            # Stack the epochs of the events for this condition
                            if epochs:
                                epochs = np.vstack(epochs)

                        # If no epochs were found for this condition, skip it
                        if len(epochs) == 0:
                            _log_with_store(f"⚠️ No valid epochs for '{cond}' in file '{file}'. Skipping.",'warning')
                            continue

                        # Get the indices of rejected epochs
                        # thres_mean = np.nanmean(processed_signal, axis=0)
                        # thres_std = np.nanstd(processed_signal, axis=0)
                        thres_mean = np.nanmean(np.nanmean(epochs, axis=1), axis=0)
                        thres_std = np.nanmean(np.nanstd(epochs, axis=1), axis=0)

                        prc_rejected, _, idx_reject = medusa.artifact_removal.reject_noisy_epochs(
                            epochs, thres_mean, thres_std, k=thres_k, n_samp=thres_samples, n_cha=thres_channels)

                        # Store the rejected indices for the current condition
                        idx_threshold[cond] = idx_reject
                        
                        # Store rejection summary
                        n_rejected = int((prc_rejected * epochs.shape[0])/100)
                        parts = base_name.split('_')
                        subj_id = next((p for p in parts if p.startswith("sub-")), base_name)
                        rejection_summary.append({
                            'subject': subj_id,
                            'condition': cond,
                            'prc_rejected': np.round(prc_rejected,2),
                            'n_rejected': n_rejected
                        })

                        del epochs  # Free memory

                # Update the progress bar and labels
                global_progress = (i*steps_per_file + 3) / total_steps * 100
                self.progress.emit(int(global_progress))

                ## Third step: Band segmentation
                # For each band...
                for j, band in enumerate(bands):
                    # Band info
                    band_name = band['name']
                    bp_min, bp_max = band['min'], band['max']

                    # Workaround to allow filtering in the Nyquist frequency
                    if bp_max == settings_dic['preprocessing']['fs'] / 2:
                        bp_max -= 1e-6

                    # If the band is not broadband, apply band filtering (the broadband does not require filtering)
                    if band_name != 'broadband':
                        processed_signal_band = band_filtering(deepcopy(processed_signal), bp_min, bp_max, fs, settings_dic['preprocessing'])
                    else:
                        processed_signal_band = deepcopy(processed_signal)

                    # Update the progress bar and labels
                    global_progress = (i * steps_per_file + 3 + j * steps_per_band + 1) / total_steps * 100
                    self.progress.emit(int(global_progress))

                    # Create a copy of the data to store the preprocessed signal (to be saved if required)
                    data_preprocessed = deepcopy(data)
                    # Get the current signal (e.g., eeg) from the data
                    biosignal = getattr(data_preprocessed, name_signal)
                    # Modify it with the preprocessed signal. It will also be modified in the data_preprocessed object
                    setattr(biosignal, "signal", processed_signal_band)
                    # Save de original signal
                    setattr(biosignal, "original_signal", original_signal)

                    # Deepcopy the data to avoid modifying the original data object
                    save_outputs(self, deepcopy(data_preprocessed), base_name, band_name, None, None, 'prep', settings_dic['save'])

                    ## Fourth step: Segmentation
                    # For each condition selected...
                    for k, cond in enumerate(settings_dic['segmentation']['selected_conditions']):

                        # If segmentation type is 'condition'
                        if settings_dic['segmentation']['segmentation_type'] == 'condition':
                            # Get epochs for the current condition
                            epochs = get_epochs_from_condition(
                                processed_signal_band, cond, signal_marks, signal_times, fs, settings_dic['segmentation'])

                        elif settings_dic['segmentation']['segmentation_type'] == 'event':
                            # Get all the selected events for this condition
                            epochs = []
                            idx_events = []
                            for evt in settings_dic['segmentation']['selected_events']:
                                try:
                                    epochs_tmp = get_epochs_from_condition(
                                        processed_signal_band, cond, signal_marks, signal_times, fs, settings_dic['segmentation'],
                                        event=evt)
                                except KeyError as err:
                                    key = err.args[0]
                                    _log_with_store(f"⚠️ No valid epochs for event '{key}' in file '{file}'. Continuing...",'warning')
                                    continue
                                if epochs_tmp is not None:
                                    epochs.append(epochs_tmp)
                                    # Store the event label for each epoch
                                    evt_key = signal_marks.app_settings['events'][evt]['label']
                                    idx_events.append(np.full((epochs_tmp.shape[0], 1), evt_key))
                                    del epochs_tmp
                                else:
                                    _log_with_store(f"⚠️ No valid epochs for event '{evt}' in file '{file}'. Continuing...",'warning')
                                    continue
                            # Stack the epochs for all the events (and their corresponding event labels)
                            if epochs:
                                epochs = np.vstack(epochs)
                                idx_events = np.vstack(idx_events)

                        # If no epochs were found for this condition, skip it
                        if len(epochs) == 0:
                            _log_with_store(f"⚠️ No valid epochs for '{cond}' in file '{file}'. Skipping.",'warning')
                            continue

                        # Update the progress bar and labels
                        global_progress = (i * steps_per_file + 3 + j * steps_per_band + 1 + k * steps_per_cond + 1) / total_steps * 100
                        self.progress.emit(int(global_progress))


                        ## Fifth step: Apply thresholding rejection if enabled
                        if settings_dic['segmentation']["thresholding"]:
                            # If all the epochs are rejected, skip this condition
                            if all(idx_threshold[cond]):
                                _log_with_store(f"⚠️ All epochs corresponding to condition '{cond}' in file '{file}' have been rejected. Skipping.",'warning')
                                continue

                            # Remove the rejected epochs from the epochs array
                            epochs = np.delete(epochs, idx_threshold[cond], axis=0)
                            # Also remove the discarded epochs from idx_events if segmentation type is 'event'
                            if settings_dic['segmentation']['segmentation_type'] == 'event':
                                idx_events = np.delete(idx_events, idx_threshold[cond], axis=0)

                        # Update the progress bar and labels
                        global_progress = (i * steps_per_file + 3 + j * steps_per_band + 1 + k * steps_per_cond + 2) / total_steps * 100
                        self.progress.emit(int(global_progress))

                        ## Sixth step: Apply resampling if enabled
                        if epochs is not None and settings_dic['segmentation']['resample']:
                            resample_fs = settings_dic['segmentation']['resample_fs']
                            window = [0, (epochs.shape[1] / fs) * 1000]  # Window in ms
                            epochs = medusa.resample_epochs(epochs, window, resample_fs)

                        # Update the progress bar and labels
                        global_progress = (i * steps_per_file + 3 + j * steps_per_band + 1 + k * steps_per_cond + 3) / total_steps * 100
                        self.progress.emit(int(global_progress))

                        # Save the segmented signals (if required), separately for each condition (and event, if selected)
                        if settings_dic['segmentation']['segmentation_type'] == 'condition':
                            save_outputs(self, deepcopy(epochs), base_name, band_name, cond, None, 'seg', settings_dic['save'])
                        elif settings_dic['segmentation']['segmentation_type'] == 'event':
                            for evt in np.unique(idx_events):
                                # Get the epochs corresponding to the current event
                                current_epochs = epochs[(idx_events.ravel() == evt),:,:]
                                # Get the event name from its label
                                event_name = None
                                for key, info in signal_marks.app_settings['events'].items():
                                    if info['label'] == evt:
                                        event_name = key
                                        break
                                save_outputs(self, deepcopy(current_epochs), base_name, band_name, cond, event_name, 'seg', settings_dic['save'])

                        if n_cha == 1:
                            epochs = epochs[:, :, None]

                        ## Seventh step: Parameter computation
                        if settings_dic['segmentation']['segmentation_type'] == 'condition':
                            params = compute_parameters(epochs, fs, band, settings_dic)
                            save_outputs(self, deepcopy(params), base_name, band_name, cond, None, 'param', settings_dic['save'])
                        elif settings_dic['segmentation']['segmentation_type'] == 'event':
                            for evt in np.unique(idx_events):
                                # Get the epochs corresponding to the current event
                                current_epochs = epochs[(idx_events.ravel() == evt),:,:]
                                current_params = compute_parameters(current_epochs, fs, band, settings_dic)
                                # Get the event name from its label
                                event_name = None
                                for key, info in signal_marks.app_settings['events'].items():
                                    if info['label'] == evt:
                                        event_name = key
                                        break
                                save_outputs(self, deepcopy(current_params), base_name, band_name, cond, event_name, 'param', settings_dic['save'])
                        # Update the progress bar and labels
                        global_progress = (i * steps_per_file + 3 + j * steps_per_band + 1 + k * steps_per_cond + 7) / total_steps * 100
                        self.progress.emit(int(global_progress))

            # Exception handling
            except Exception as e:
                error_found = True
                _log_with_store(f"Error preprocessing {file}: {e}",'error')
                self.text_progress.emit("Error")

        # Save logs and summary
        try:
            selected_folder = Path(settings_dic['save']["folder"])
            derivatives_path = selected_folder / "derivatives"
            derivatives_path.mkdir(exist_ok=True)
            
            # Save rejection summary to CSV
            if rejection_summary:
                csv_path = derivatives_path / "rejection_summary.csv"
                with open(csv_path, mode='w', newline='') as csv_file:
                    fieldnames = ['subject', 'condition', 'prc_rejected', 'n_rejected']
                    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                    writer.writeheader()
                    for row in rejection_summary:
                        writer.writerow(row)
                    row = {
                        'subject': f"K STDs: {settings_dic['segmentation']['thres_k']}",
                        'condition': f"Samples: {settings_dic['segmentation']['thres_samples']}",
                        'prc_rejected': f"N Channels: {settings_dic['segmentation']['thres_channels']}"
                    }
                    writer.writerow(row)
                self.log.emit(f"✅ Rejection summary saved to {csv_path}", "")

            # Save execution warnings/errors to TXT
            if execution_logs:
                log_path = derivatives_path / "error_log.txt"
                with open(log_path, mode='w', encoding='utf-8') as txt_file:
                    for log_entry in execution_logs:
                        txt_file.write(log_entry + "\n")
                self.log.emit(f"✅ Execution logs saved to {log_path}", "")

        except Exception as e:
            self.log.emit(f"⚠️ Could not save logs/summary: {e}", "warning")

        self.text_progress.emit("Completed")

        return error_found

#################### HELPER FUNCTIONS

def include_no_conditions_in_marks(marks, times):
    # Create a copy of marks
    new_marks = deepcopy(marks)

    # The label for no-condition will be the max label + 1
    if marks.conditions_labels:
        new_label = np.max(marks.conditions_labels) + 1
    else:
        new_label = 0
    # Include the no-condition condition in the app_settings
    new_marks.app_settings['conditions']['nocondition'] = {'desc-name': 'No Condition',
                                                             'label': new_label,
                                                             'shortcut': 'NA'}

    # Get the conditions times and labels from the original marks
    conditions_times = np.array(marks.conditions_times).reshape(-1, 2)
    conditions_labels = np.array(marks.conditions_labels).reshape(-1, 2)[:,0]

    # Convert the times to indices of the 'times' array
    ranges = []
    # For each condition
    for (start_t, end_t), label in zip(conditions_times, conditions_labels):
        # Get the closest indices in 'times' for the initial and final timestamps
        start_idx = np.searchsorted(times, start_t)
        end_idx = np.searchsorted(times, end_t)
        # Append them in the ranges variable
        ranges.append((start_idx, end_idx, label))

    if ranges:
        # Add intervals where there is no label with "new_label" (i.e., fill the no-condition gaps)
        final_ranges = []
        prev_end = 0
        # For each range in ranges
        for start, end, label in ranges:
            # Check if there is a gap between the previous end and the current start
            if prev_end < start:
                # If so, append a new range with label "new_label"
                final_ranges.append((prev_end, start, new_label))
            # Append the current range (the range of the already existing condition)
            final_ranges.append((start, end, label))
            # The current end becomes the previous end for the next iteration
            prev_end = end
    else:
        # If there are no ranges (no conditions), the entire signal is no-condition
        final_ranges = [(0, len(times), new_label)]
        prev_end = len(times)

    # If there is a gap between the last end and the end of the signal, also append it as a "new_label" (i.e.,
    # no-condition) range
    if prev_end < len(times):
        final_ranges.append((prev_end, len(times), new_label))

    # Create the new conditions_times and conditions_labels arrays
    new_conditions_times = []
    new_conditions_labels = []
    # For each range in final_ranges
    for start_idx, end_idx, label in final_ranges:
        # Append the start and end times. The end_idx is actually the beginning of the next range, so we use end_idx - 1
        # to get the actual end time of the current range
        new_conditions_times.append([times[start_idx], times[end_idx - 1]])
        # Append the label twice (start and end)
        new_conditions_labels.append(label)
        new_conditions_labels.append(label)
    # Convert to numpy arrays
    new_conditions_times = np.array(new_conditions_times).flatten() # Flatten the array
    new_conditions_labels = np.array(new_conditions_labels)

    # Include the new conditions times and labels in the new marks
    new_marks.conditions_times = new_conditions_times
    new_marks.conditions_labels = new_conditions_labels

    return new_marks


def get_epochs_from_condition(signal, condition, marks, times, fs, cfg, event=None):
    """
    Extract epochs from the signal based on specified condition names
    """
    # Fs
    fs_seg = fs / 1000
    # Trial length
    trial_len = int(cfg['trial_length']) * fs_seg if cfg['trial_length'] else None
    # Trial stride
    trial_stride_val = cfg['trial_stride']
    trial_stride = (trial_stride_val / 100 * trial_len) if trial_stride_val else None
    # Event window
    w_start, w_end = cfg['window_start'], cfg['window_end']
    window = [w_start, w_end]
    # Event baseline
    baseline_window = [cfg['baseline_start'],
                       cfg['baseline_end']] if cfg['norm'] else None
    # Normalization
    norm_type = cfg['norm_type'] if cfg['norm'] else None

    # Get the label (numerical value) associated with the condition name
    cond_key = marks.app_settings['conditions'][condition]['label']
    if event:
        evt_key = marks.app_settings['events'][event]['label']
    # Find indices of epochs matching the condition label
    idx = np.where(np.array(marks.conditions_labels) == cond_key)[0]
    # Skip if odd number of indices (requires pairs of start/end)
    if len(idx) % 2 != 0:
        return False

    # Segment into epochs
    segments = []
    # For each pair of start/end indices
    for i in range(0, len(idx), 2):
        # Start and end sample indices of the conditions
        start = _find_nearest_index(times, marks.conditions_times[idx[i]])
        end = _find_nearest_index(times, marks.conditions_times[idx[i + 1]])
        if event:
            # Get start and end times
            start_time, end_time = times[start], times[end]
            # Get the event indices within the condition time range
            evt_idx = _get_event_indices_in_range(marks, evt_key, start_time, end_time)
            if evt_idx.size == 0:
                return None
            # Get the times of the events within the condition time range
            onsets = np.array(marks.events_times)[evt_idx]
            # Get epochs from these events
            epochs = medusa.get_epochs_of_events(times, signal, onsets, fs, window, baseline_window, norm=norm_type)
        else:
            # Extract segment
            segment = signal[start:end]
            # Get epochs from the segment
            epochs = medusa.get_epochs(segment, trial_len, stride=trial_stride, norm=norm_type)

        # Append if epochs were created
        if epochs is not None:
            segments.append(epochs)

    # Set the dimensions of the epoched data
    epoched = np.concatenate(segments, axis=0) if segments else None
    return epoched
def _find_nearest_index(reference_times, query_times):
    """
    Find the index (or indices) in reference_times closest to query_times.
    """
    # References times is the times vector
    reference_times = np.asarray(reference_times)
    # Query times is the markers of the events/conditions
    query_times = np.atleast_1d(query_times)  # Ensure we always work with an array (i.e., convert scalars to 1D array)

    # Find indices where query_times would be inserted into reference_times to keep order
    indices = np.searchsorted(reference_times, query_times)

    # In the next step we will index using "indices" and "indices - 1". This means that we now have to avoid indices
    # being 0 or len(reference_times), as this would lead to out-of-bounds indexing in the next step. We will clip the
    # indices so that all of their values are between 1 and len(reference_times) - 1, ensuring that both "indices" and
    # "indices - 1" are within valid range (i.e., not 0 and not len(reference_times))
    indices = np.clip(indices, 1, len(reference_times) - 1)

    # Get the left and right neighbors of each query time
    left = reference_times[indices - 1]
    right = reference_times[indices]

    # Choose the closest neighbor (right or left)
    choose_left = np.abs(query_times - left) < np.abs(query_times - right) # Choose left if it's closer than right
    # nearest_indices will contain indices - 1 if left is closer, or indices if right is closer
    nearest_indices = np.where(choose_left, indices - 1, indices)

    # If the input was a single value, return a single index. This if covers two ways of providing a single value: as a
    # scalar and as a one-element array
    if np.isscalar(query_times) or query_times.shape == (1,):
        return nearest_indices[0]

    # If the input was an array, return an array of indices
    return nearest_indices
def _get_event_indices_in_range(marks, event_key, start_time, end_time):
    """
    Return indices of events that occur within a given time interval.
    """
    events_labels = np.array(marks.events_labels)
    events_times = np.array(marks.events_times)
    return np.where(
        (events_labels == event_key) &
        (events_times >= start_time) &
        (events_times <= end_time))[0]


def save_outputs(worker, data, base_name, band_name, cond, event, key, settings_dic):
    """
    Guarda los resultados del pipeline en estructura semi-BIDS dentro de /derivatives.

    Estructura:
    derivatives/
        ├── preprocessed/
        ├── segmented/
        └── parameters/
    """
    selected_folder = Path(settings_dic["folder"])
    derivatives_path = selected_folder / "derivatives"
    derivatives_path.mkdir(exist_ok=True)

    # Obtener info del sujeto y sesión desde el nombre del archivo base
    parts = base_name.split('_')
    subj_id = next((p for p in parts if p.startswith("sub-")), None)
    ses_id = next((p for p in parts if p.startswith("ses-")), None)
    base_stem = Path(base_name).stem
    # --- Saving preprocessed signals (.rec.bson) ---
    if key == "prep" and settings_dic["save_preproc"]:
        if ses_id:
            preproc_dir = derivatives_path / "preprocessed" / subj_id / ses_id / "EEG"
        else:
            preproc_dir = derivatives_path / "preprocessed" / subj_id / "EEG"
        preproc_dir.mkdir(parents=True, exist_ok=True)

        output_path = preproc_dir / f"{base_stem}_band-{band_name.replace('-', '')}.rec.bson"
        if hasattr(data, "save"):
            data.save(str(output_path))
        elif hasattr(data, "save_to_bson"):
            data.save_to_bson(str(output_path))
        else:
            raise RuntimeError('Error saving')

        worker.log.emit(f"✅ Preprocessed saved: {output_path}","")

    # --- Saving segmented signals (.mat) ---
    if key == "seg" and settings_dic["save_segmented"]:
        if ses_id:
            seg_dir = derivatives_path / "segmented" / subj_id / ses_id / "EEG"
        else:
            seg_dir = derivatives_path / "segmented" / subj_id / "EEG"
        seg_dir.mkdir(parents=True, exist_ok=True)

        if event is not None:
            output_name = f"{base_stem}_band-{band_name.replace('-', '')}_cond-{cond.replace('-', '')}_event-{event.replace('-', '')}.mat"
        else:
            output_name = f"{base_stem}_band-{band_name.replace('-', '')}_cond-{cond.replace('-', '')}.mat"
        output_path = seg_dir / output_name

        savemat(output_path, {'epochs': data})
        worker.log.emit(f"✅ Segmented saved: {output_path}","")

    # --- Saving parameters (.mat) ---
    if key == "param" and settings_dic["save_params"]:
        if ses_id:
            param_dir = derivatives_path / "parameters" / subj_id / ses_id / "EEG"
        else:
            param_dir = derivatives_path / "parameters" / subj_id / "EEG"
        param_dir.mkdir(parents=True, exist_ok=True)

        if not isinstance(data, dict):
            if event is not None:
                outname = f"{subj_id}_param-unknown_band-{band_name.replace('-', '')}_cond-{cond.replace('-', '')}_event-{event.replace('-', '')}.mat"
            else:
                outname = f"{subj_id}_param-unknown_band-{band_name.replace('-', '')}_cond-{cond.replace('-', '')}.mat"
            outpath = param_dir / outname
            savemat(outpath, {'parameters': data})
            worker.log.emit(f"⚠️ Parameters: saved fallback file {outpath}","")
            return

        params_dict = dict(data)

        # 1) PSDs: (psd_<band> + psd_freqs_<band>)
        psd_bands = set()
        for k in list(params_dict.keys()):
            if k.startswith('psd_'):
                psd_bands.add(k[4:])
            if k.startswith('psdfreqs_'):
                psd_bands.add(k[10:])

        for b in psd_bands:
            psd_key = f'psd{b}'
            freqs_key = f'psdfreqs{b}'
            psd_val = params_dict.pop(psd_key, None)
            freqs_val = params_dict.pop(freqs_key, None)

            metric_label = (f"psd{b}")
            if event is not None:
                outname = f"{base_stem}_param-{metric_label.replace('-', '')}_band-{band_name.replace('-', '')}_cond-{cond.replace('-', '')}_event-{event.replace('-', '')}.mat"
            else:
                outname = f"{base_stem}_param-{metric_label.replace('-', '')}_band-{band_name.replace('-', '')}_cond-{cond.replace('-', '')}.mat"
            outpath = param_dir / outname

            save_struct = {}
            if psd_val is not None:
                save_struct['psd'] = np.asarray(psd_val)
            if freqs_val is not None:
                save_struct['freqs'] = np.asarray(freqs_val)

            mat_dict = {metric_label: save_struct}

            savemat(outpath, mat_dict)
            worker.log.emit(f"✅ Parameter saved: {outpath}","")

        # 2) Other parameters
        for k, v in list(params_dict.items()):
            metric_label = k.replace('_', '-')

            if event is not None:
                outname = f"{base_stem}_param-{metric_label.replace('-', '')}_band-{band_name}_cond-{cond}_event-{event.replace('-', '')}.mat"
            else:
                outname = f"{base_stem}_param-{metric_label.replace('-', '')}_band-{band_name.replace('-', '')}_cond-{cond.replace('-', '')}.mat"
            outpath = param_dir / outname

            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict) and 'band' in v[0]:
                for entry in v:
                    bname = entry.get('band', 'unknown')
                    val = np.asarray(entry.get('value'))

                    # Nombre del archivo: usa la banda del diccionario, NO la del argumento
                    if event is not None:
                        outname = (
                            f"{base_stem}_param-{metric_label.replace('-', '')}_band-{bname.replace('-', '')}"
                            f"_cond-{cond.replace('-', '')}_event-{event.replace('-', '')}.mat"
                        )
                    else:
                        outname = (
                            f"{base_stem}_param-{metric_label.replace('-', '')}_band-{bname.replace('-', '')}"
                            f"_cond-{cond.replace('-', '')}.mat"
                        )

                    outpath = param_dir / outname
                    savemat(outpath, {
                        "param": val,
                        "info": metric_label
                    })
                    worker.log.emit(f"✅ Parameter saved: {outpath}","")

            elif isinstance(v, dict):
                nested = {}
                for kk, vv in v.items():
                    nested[kk] = np.asarray(vv)

                savemat(outpath, {
                    "param": nested,
                    "info": metric_label
                })
            else:
                try:
                    savemat(outpath, {
                        "param": np.asarray(v),
                        "info": metric_label
                    })
                except Exception:
                    savemat(outpath, {
                        "param": np.asarray(v, dtype=object),
                        "info": metric_label
                    })

            worker.log.emit(f"✅ Parameter saved: {outpath}","")

#################### PREPROCESSING

def apply_preprocessing(signal, fs, cfg):
    """
    Apply bandpass, notch filtering, and Common Average Reference (CAR).
    """
    # Bandpass filter
    if cfg.get('bandpass'):
        signal = medusa.FIRFilter(cfg['bp_order'], [cfg['bp_min'], cfg['bp_max']], 'bandpass',
                                  window=cfg['bp_win']).fit_transform(signal, fs)
    # Notch filter
    if cfg.get('notch'):
        signal = medusa.FIRFilter(cfg['notch_order'], [cfg['notch_min'], cfg['notch_max']],
                                  'bandstop', window=cfg['notch_win']).fit_transform(signal, fs)

    # CAR and return
    return medusa.car(signal) if cfg.get('car') else signal


##################### BAND FILTERING

def band_filtering(signal, bp_min, bp_max, fs, cfg):
    """
    Apply band segmentation with a FIR bandpass filter. Used when preprocessing is disabled but band-specific
    segmentation is required.
    """
    order = 1000 if cfg['bandpass'] is False else cfg['bp_order']
    win = 'hamming' if cfg['bandpass'] is False else cfg['bp_win']
    bp_filter = medusa.FIRFilter(order, [bp_min, bp_max], 'bandpass', window=win)
    signal = bp_filter.fit_transform(signal, fs)
    return signal

##################### BAND FILTERING

def compute_parameters(epochs, fs, band, cfg):
    # Initialize dict that will contain all the computed parameters
    params = {}


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
        if cfg['parameters'][name]:
            # Compute it
            val = func(epochs, axis=axis)
            # Average across epochs if required and if multiple epochs are present
            val = np.mean(val, axis=0) if cfg['segmentation']['average'] and epochs.ndim == 3 else val
            # Store in the params dict
            params[f"{name}"] = val


    ## POWER SPECTRAL DENSITY (PSD)
    # PSD would be computed if explicitly selected
    explicit_psd = cfg['parameters']['psd']
    # Or if any parameter that depends on it is selected
    params_require_psd = any([cfg['parameters'][spec_param]
        for spec_param in ['absolute_power', 'median_frequency', 'spectral_entropy','relative_power']])
    require_psd = explicit_psd or params_require_psd

    if require_psd:
        # Use user-defined parameters for segmenting and windowing
        segment_psd = cfg['parameters']['psd_segment_pct']
        overlap_psd = cfg['parameters']['psd_overlap_pct']
        window_psd = cfg['parameters']['psd_window']

        # Compute PSD using specified segment and window settings
        fxx, psd = medusa.transforms.power_spectral_density(epochs, fs, segment_psd, overlap_psd, window_psd)

        # Store PSD values: average across trials if averaging is enabled
        try:
            psd_values = np.nanmean(psd, axis=0) if cfg['segmentation']['average'] and epochs.ndim == 3 else psd
            params['psd'] = {
                'values': psd_values,
                'freqs': fxx
            }
        except Exception as e:
            print(e)

    ## SPECTRAL METRICS - RELATIVE POWER
    # Only compute the RP in the broadband, and if explicitly selected
    if band['name'] == 'broadband' and cfg['parameters']['relative_power']:
        val = []

        # The bands will be different if band segmentation is enabled or not
        if cfg['preprocessing']['band_segmentation']:
            selected_bands = cfg['preprocessing']['selected_bands']
        else:
            selected_bands = cfg['parameters']['selected_rp_bands']

        # # Define broadband range, as the minimum of the mins and the maximum of the maxs of the selected bands
        # min_val = min(band["min"] for band in selected_bands if band["name"] != 'broadband')
        # max_val = max(band["max"] for band in selected_bands if band["name"] != 'broadband')
        # Define broadband range based on the broadband limits
        min_val = band['min'] # Now band is broadband (condition above), so we can use its min and max values to define the range
        max_val = band['max']

        # Loop through each selected band
        for band_rp in selected_bands:
            if band_rp["name"] != 'broadband':
                # Define band parameters
                band_range = [band_rp["min"], band_rp["max"]]
                # Compute the metric
                val_band = medusa.signal_metrics.band_power.band_power(psd, fs, band_range, 'relative', [min_val, max_val])
                # Average across epochs if required and if multiple epochs are present
                val_band = np.nanmean(val_band, axis=0) if cfg['segmentation']['average'] and epochs.ndim == 3 else val_band
                val.append({"band": band_rp["name"], "value": val_band})

            params[f"relative_power"] = val

    ## SPECTRAL METRICS - OTHERS
    spectral_funcs = {
        "absolute_power": medusa.signal_metrics.band_power.band_power,
        "median_frequency": medusa.signal_metrics.median_frequency.median_frequency,
        "spectral_entropy": medusa.signal_metrics.shannon_spectral_entropy.shannon_spectral_entropy,
    }

    # For each parameter...
    for name, func in spectral_funcs.items():
        # If selected...
        if cfg['parameters'][name]:
            # Get the current band range
            band_range = [band['min'], band['max']]
            # Compute the metric
            if name == 'absolute_power':
                val = func(psd, fs, band_range, 'absolute')
            else:
                val = func(psd, fs, band_range)
            # Average across epochs if required and if multiple epochs are present
            val = np.nanmean(val, axis=0) if cfg['segmentation']['average'] and epochs.ndim == 3 else val
            # Store in the params dict
            params[f"{name}"] = val

    ## NONLINEAR METRICS
    nonlinear_funcs = {
        'ctm': lambda: medusa.signal_metrics.central_tendency.central_tendency_measure(epochs,
            cfg['parameters']['ctm_r']),
        'sample_entropy': lambda: medusa.signal_metrics.sample_entropy.sample_entropy(epochs,
            cfg['parameters']['sample_entropy_m'], cfg['parameters']['sample_entropy_r']),
        'multiscale_sample_entropy': lambda: medusa.signal_metrics.multiscale_entropy.multiscale_entropy(
            epochs, cfg['parameters']['multiscale_sample_entropy_scale'],cfg['parameters']['multiscale_sample_entropy_m'],
            cfg['parameters']['multiscale_sample_entropy_r']),
        'lzc': lambda: medusa.signal_metrics.lempelziv_complexity.lempelziv_complexity(epochs),
        'multiscale_lzc': lambda: medusa.signal_metrics.multiscale_lempelziv_complexity.multiscale_lempelziv_complexity(
            epochs,cfg['parameters']['multiscale_lzc_scales'])}

    # For each parameter...
    for name, func in nonlinear_funcs.items():
        # If selected...
        if cfg['parameters'][name]:
            # Compute it
            val = func()
            # Average across epochs if required and if multiple epochs are present
            val = np.nanmean(val, axis=0) if cfg['segmentation']['average'] and epochs.ndim == 3 else val
            params[f"{name}"] = val


    ## CONNECTIVITY METRICS
    connectivity_funcs = {
        'iac': lambda: medusa.connectivity_metrics.iac(epochs, cfg['parameters']['ort_iac']),
        'aec': lambda: medusa.connectivity_metrics.aec(epochs, cfg['parameters']['ort_aec']),
        'plv': lambda: medusa.connectivity_metrics.plv(epochs),
        'pli': lambda: medusa.connectivity_metrics.pli(epochs),
        'wpli': lambda: medusa.connectivity_metrics.wpli(epochs),
    }

    # For each parameter...
    for name, func in connectivity_funcs.items():
        # If selected...
        if cfg['parameters'][name]:
            # Compute it
            val = func()
            # Average across epochs if required and if multiple epochs are present
            val = np.nanmean(val, axis=0) if cfg['segmentation']['average'] and epochs.ndim == 3 else val
            params[f"{name}"] = val

    return params

def load_config(files_widget, data):

    # BIOSIGNAL INFO
    biosignal_txt = files_widget.biosignalBox.currentText()
    biosignal = biosignal_txt.split(" ")[1]
    files_widget.controller.biosignal_info = files_widget.controller.biosignals[biosignal]

    # PREPROCESSING
    prep_cfg = data["preprocessing"]
    preproc_widget = files_widget.main_window.stackedWidget.widget(2)  # widget(2) is the preprocessing widget
    preproc_widget.minbroadBox.setValue(prep_cfg['broadband_min'])
    preproc_widget.maxbroadBox.setValue(prep_cfg['broadband_max'])
    preproc_widget.preprocessingButton.setChecked(bool(prep_cfg["apply_preprocessing"]))
    preproc_widget.notchCBox.setChecked(bool(prep_cfg['notch']))
    preproc_widget.minfreqnotchBox.setValue(
        prep_cfg['notch_min'] if prep_cfg['notch_min'] is not None else preproc_widget.defaults["minfreqnotch"])
    preproc_widget.maxfreqnotchBox.setValue(
        prep_cfg['notch_max'] if prep_cfg['notch_max'] is not None else preproc_widget.defaults["minfreqnotch"])
    preproc_widget.orderNotchBox.setValue(
        prep_cfg['notch_order'] if prep_cfg['notch_order'] is not None else preproc_widget.defaults["ordernotch"])
    preproc_widget.winnotchBox.setCurrentText(prep_cfg['notch_win'])
    preproc_widget.bpCBox.setChecked(bool(prep_cfg['bandpass']))
    preproc_widget.minfreqbpBox.setValue(
        prep_cfg['bp_min'] if prep_cfg['bp_min'] is not None else preproc_widget.defaults["minfreqbp"])
    preproc_widget.maxfreqbpBox.setValue(
        prep_cfg['bp_max'] if prep_cfg['bp_max'] is not None else preproc_widget.defaults["maxfreqbp"])
    preproc_widget.orderbpBox.setValue(
        prep_cfg['bp_order'] if prep_cfg['bp_order'] is not None else preproc_widget.defaults["orderbp"])
    preproc_widget.winbpBox.setCurrentText(prep_cfg['bp_win'])
    preproc_widget.carCBox.setChecked(bool(prep_cfg['car']))
    preproc_widget.bandCBox.setChecked(bool(prep_cfg['band_segmentation']))
    bands_list = prep_cfg.get("selected_bands") or []
    bands = bands_list[1:] if len(bands_list) > 1 else []  # Exclude 'broadband' if other bands are present
    if bands:
        preproc_widget.controller.update_band_label("segmentation", bands)
    # Store
    files_widget.main_window.controller.preproc_config = prep_cfg

    # SEGMENTATION
    segm_cfg = data["segmentation"]
    segm_widget = files_widget.main_window.stackedWidget.widget(3)  # widget(3) is the segmentation widget
    segm_widget.conditionRButton.setChecked(
        segm_cfg['segmentation_type'] == 'condition')  # RButton, so it is exclusive with eventRButton
    segm_widget.trialBox.setValue(
        segm_cfg['trial_length'] if segm_cfg['trial_length'] is not None else segm_widget.defaults['triallength'])
    segm_widget.trialstrideBox.setValue(
        segm_cfg['trial_stride'] if segm_cfg['trial_stride'] is not None else segm_widget.defaults['trialstride'])
    segm_widget.winBox_1.setValue(
        segm_cfg['window_start'] if segm_cfg['window_start'] is not None else segm_widget.defaults['windowbox1'])
    segm_widget.winBox_2.setValue(
        segm_cfg['window_end'] if segm_cfg['window_end'] is not None else segm_widget.defaults['windowbox2'])
    segm_widget.normCBox.setChecked(bool(segm_cfg['norm']))
    if segm_cfg['norm_type'] == 'z':
        segm_widget.zscoreRButton.setChecked(True)  # RButton, so it is exclusive with dcRButton
    segm_widget.baselineCBox_1.setValue(
        segm_cfg['baseline_start'] if segm_cfg['baseline_start'] is not None else segm_widget.defaults['baselinewin1'])
    segm_widget.baselineCBox_2.setValue(
        segm_cfg['baseline_end'] if segm_cfg['baseline_end'] is not None else segm_widget.defaults['baselinewin2'])
    segm_widget.averageCBox.setChecked(bool(segm_cfg['average']))
    segm_widget.thresCBox.setChecked(bool(segm_cfg['thresholding']))
    segm_widget.threskBox.setValue(
        segm_cfg['thres_k'] if segm_cfg['thres_k'] is not None else segm_widget.defaults['threshold'])
    segm_widget.thressampBox.setValue(
        segm_cfg['thres_samples'] if segm_cfg['thres_samples'] is not None else segm_widget.defaults['thressamples'])
    segm_widget.threschanBox.setValue(
        segm_cfg['thres_channels'] if segm_cfg['thres_channels'] is not None else segm_widget.defaults['threschannels'])
    segm_widget.resampleCBox.setChecked(bool(segm_cfg['resample']))
    segm_widget.resamplefsBox.setValue(
        segm_cfg['resample_fs'] if segm_cfg['resample_fs'] is not None else segm_widget.defaults['resamplefs'])
    # Store
    files_widget.main_window.controller.segmentation_config = segm_cfg

    # PARAMETERS
    params_cfg = data["parameters"]
    params_widget = files_widget.main_window.stackedWidget.widget(4)  # widget(4) is the parameters widget
    params_widget.meanCBox.setChecked(bool(params_cfg['mean']))
    params_widget.medianCBox.setChecked(bool(params_cfg['median']))
    params_widget.varianceCBox.setChecked(bool(params_cfg['variance']))
    params_widget.kurtosisCBox.setChecked(bool(params_cfg['kurtosis']))
    params_widget.skewnessCBox.setChecked(bool(params_cfg['skewness']))
    params_widget.psdCBox.setChecked(bool(params_cfg['psd']))
    params_widget.segmentpsdBox.setValue(
        params_cfg['psd_segment_pct'] if params_cfg['psd_segment_pct'] is not None else params_widget.defaults[
            'psdsegment'])
    params_widget.overlappsdBox.setValue(
        params_cfg['psd_overlap_pct'] if params_cfg['psd_overlap_pct'] is not None else params_widget.defaults[
            'psdoverlap'])
    params_widget.psdcomboBox.setCurrentText(params_cfg['psd_window'])
    params_widget.controller.loading_config = True
    params_widget.rpCBox.setChecked(bool(params_cfg['relative_power']))
    params_widget.controller.update_band_label('rp', params_cfg["selected_rp_bands"])
    params_widget.controller.loading_config = False
    params_widget.apCBox.setChecked(bool(params_cfg['absolute_power']))
    params_widget.mfCBox.setChecked(bool(params_cfg['median_frequency']))
    params_widget.seCBox.setChecked(bool(params_cfg['spectral_entropy']))
    params_widget.ctmCBox.setChecked(bool(params_cfg['ctm']))
    params_widget.ctmrBox.setValue(
        params_cfg['ctm_r'] if params_cfg['ctm_r'] is not None else params_widget.defaults['ctmradius'])
    params_widget.sampenCBox.setChecked(bool(params_cfg['sample_entropy']))
    params_widget.sampenrBox.setValue(
        params_cfg['sample_entropy_r'] if params_cfg['sample_entropy_r'] is not None else params_widget.defaults[
            'sampradius'])
    params_widget.sampenmBox.setValue(
        params_cfg['sample_entropy_m'] if params_cfg['sample_entropy_m'] is not None else params_widget.defaults[
            'sampm'])
    params_widget.msampenCBox.setChecked(bool(params_cfg['multiscale_sample_entropy']))
    params_widget.msampenrBox.setValue(
        params_cfg['multiscale_sample_entropy_r'] if params_cfg['multiscale_sample_entropy_r'] is not None else
        params_widget.defaults['multisampradius'])
    params_widget.msampenmBox.setValue(
        params_cfg['multiscale_sample_entropy_m'] if params_cfg['multiscale_sample_entropy_m'] is not None else
        params_widget.defaults['multisampm'])
    params_widget.msampenscaleBox.setValue(
        params_cfg['multiscale_sample_entropy_scale'] if params_cfg['multiscale_sample_entropy_scale'] is not None else
        params_widget.defaults['multisampmaxscale'])
    params_widget.lzcCBox.setChecked(bool(params_cfg['lzc']))
    params_widget.mlzcCBox.setChecked(bool(params_cfg['multiscale_lzc']))
    if params_cfg['multiscale_lzc_scales'] is not None:
        params_widget.mlzcEdit.setText(str(params_cfg['multiscale_lzc_scales']))
    params_widget.iacCBox.setChecked(bool(params_cfg['iac']))
    params_widget.iacortButton.setChecked(bool(params_cfg['ort_iac']))
    params_widget.aecCBox.setChecked(bool(params_cfg['aec']))
    params_widget.aecortButton.setChecked(bool(params_cfg['ort_aec']))
    params_widget.pliCBox.setChecked(bool(params_cfg['pli']))
    params_widget.plvCBox.setChecked(bool(params_cfg['plv']))
    params_widget.wpliCBox.setChecked(bool(params_cfg['wpli']))
    # Store
    files_widget.main_window.controller.parameters_config = params_cfg