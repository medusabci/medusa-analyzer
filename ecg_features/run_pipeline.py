from PySide6 import QtCore, QtGui, QtWidgets
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

from pyparsing import originalTextFor
from scipy.stats import kurtosis, skew, zscore
from scipy.io import savemat

import matplotlib.pyplot as plt

def run_pipeline(controller, settings_dic):
    """
    Main pipeline function of the eeg features extraction that executes preprocessing, segmentation, and parameter
    computation for all selected files based on the provided configuration.
    """

    # Get the selected files and associated variables
    selected_files = settings_dic['files'].get('selected_files', [])
    total_files = len(selected_files)
    error_found = False

    view = controller.view

    # Loop through each selected file
    for i, file in enumerate(selected_files):
        try:
            # Logging and GUI updates
            controller._log_message(f"Processing file: {file}")
            view.progressLabel.setText(f"Processing: {basename(file)}")
            QtWidgets.QApplication.processEvents()

            # Load data
            base_name = splitext(basename(file))[0]
            data = medusa.components.Recording.load(file)
            # Initialize variables
            name_signal = settings_dic['files']['selected_biosignal']  # ej: "eeg"
            original_signal = getattr(data, name_signal).signal
            signal_times = getattr(data, name_signal).times
            channel_set = getattr(data, name_signal).channel_set
            signal_marks = include_no_conditions_in_marks(data.marks, signal_times)
            fs = getattr(data, name_signal).fs

            # Ensure consistent sampling frequency
            if fs != settings_dic['preprocessing']['fs']:
                raise Exception("One of the selected signals do not have the same sampling frequency: " + file)

            ## First step: Select channels
            chan_idx = []
            for chan_name in settings_dic['leads']['selected_channels']:
                idx_tmp = channel_set.l_cha.index(chan_name)
                chan_idx.append(idx_tmp)
            processed_signal = deepcopy(original_signal)
            processed_signal = processed_signal[:, chan_idx]

            ## Second step: Preprocessing ECG
            if settings_dic['preprocessing']['apply_preprocessing']:
                processed_signal = apply_preprocessing_ecg(processed_signal, fs, settings_dic['preprocessing'])

            ## Third step: HRV computation
            if settings_dic['preprocessing']['hrv']:
                processed_signal =a

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
                            epochs_tmp = get_epochs_from_condition(
                                processed_signal, cond, signal_marks, signal_times, fs, settings_dic['segmentation'],
                                event=evt)
                            if epochs_tmp is not None:
                                epochs.append(epochs_tmp)
                                del epochs_tmp

                        # Stack the epochs of the events for this condition
                        if epochs:
                            epochs = np.vstack(epochs)

                    # If no epochs were found for this condition, skip it
                    if len(epochs) == 0:
                        controller._log_message(
                            f"No valid epochs for '{cond}' in file '{file}'. Skipping.",
                            style='warning')
                        continue

                    # Get the indices of rejected epochs
                    _, _, idx_reject = medusa.artifact_removal.reject_noisy_epochs(
                        epochs, np.nanmean(original_signal, axis=0), np.std(original_signal, axis=0),
                        k=thres_k, n_samp=thres_samples, n_cha=thres_channels)

                    # Store the rejected indices for the current condition
                    idx_threshold[cond] = idx_reject
                    del epochs  # Free memory

            ## Third step: Band segmentation
            # Store the bands if band segmentation is enabled, otherwise use broadband
            bands = settings_dic['preprocessing']['selected_bands'] if (
                settings_dic['preprocessing']['band_segmentation']) else [
                {'name': 'broadband', 'min': settings_dic['preprocessing']['broadband_min'],
                 'max': settings_dic['preprocessing']['broadband_max']}]
            total_steps = total_files * len(bands)

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
                    processed_signal = band_filtering(processed_signal, bp_min, bp_max, fs, settings_dic['preprocessing'])

                # Create a copy of the data to store the preprocessed signal (to be saved if required)
                data_preprocessed = deepcopy(data)
                # Get the current signal (e.g., eeg) from the data
                biosignal = getattr(data_preprocessed, name_signal)
                # Modify it with the preprocessed signal. It will also be modified in the data_preprocessed object
                setattr(biosignal, "signal", processed_signal)
                # Save de original signal
                setattr(biosignal, "original_signal", original_signal)

                # Deepcopy the data to avoid modifying the original data object
                save_outputs(controller, deepcopy(data_preprocessed), base_name, band_name, 'prep', settings_dic)

                ## Fourth step: Segmentation
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
                        idx_events = []
                        for evt in settings_dic['segmentation']['selected_events']:
                            epochs_tmp = get_epochs_from_condition(
                                processed_signal, cond, signal_marks, signal_times, fs, settings_dic['segmentation'],
                                event=evt)
                            if epochs_tmp is not None:
                                epochs.append(epochs_tmp)
                                # Store the event label for each epoch
                                evt_key = signal_marks.app_settings['events'][evt]['label']
                                idx_events.append(np.full((epochs_tmp.shape[0], 1), evt_key))
                                del epochs_tmp
                        # Stack the epochs for all the events (and their corresponding event labels)
                        if epochs:
                            epochs = np.vstack(epochs)
                            idx_events = np.vstack(idx_events)

                    # If no epochs were found for this condition, skip it
                    if len(epochs) == 0:
                        controller._log_message(
                            f"No valid epochs for '{cond}' in file '{file}'. Skipping.",
                            style='warning')
                        continue

                    ## Fifth step: Apply thresholding rejection if enabled
                    if settings_dic['segmentation']["thresholding"]:
                        # If all the epochs are rejected, skip this condition
                        if all(idx_threshold[cond]):
                            controller._log_message(
                                f"All epochs corresponding to condition '{cond}' in file '{file}' have been rejected. Skipping.",
                                style='warning')
                            continue

                        # Remove the rejected epochs from the epochs array
                        epochs = np.delete(epochs, idx_threshold[cond], axis=0)
                        # Also remove the discarded epochs from idx_events if segmentation type is 'event'
                        if settings_dic['segmentation']['segmentation_type'] == 'event':
                            idx_events = np.delete(idx_events, idx_threshold[cond], axis=0)

                    ## Sixth step: Apply resampling if enabled
                    if epochs is not None and settings_dic['segmentation']['resample']:
                        resample_fs = settings_dic['segmentation']['resample_fs']
                        window = [0, (epochs.shape[1] / fs) * 1000]  # Window in ms
                        epochs = medusa.resample_epochs(epochs, window, resample_fs)

                    # Save the segmented signals (if required), separately for each condition (and event, if selected)
                    if settings_dic['segmentation']['segmentation_type'] == 'condition':
                        save_outputs(controller, deepcopy(epochs), f"{base_name}_segmentation_{cond}", band_name, 'seg', settings_dic)
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
                            save_outputs(controller, deepcopy(current_epochs), f"{base_name}_segmentation_{cond}_{event_name}", band_name, 'seg', settings_dic)

                    ## Seventh step: Parameter computation
                    if settings_dic['segmentation']['segmentation_type'] == 'condition':
                        params = compute_parameters(epochs, fs, band, settings_dic)
                        save_outputs(controller, deepcopy(params), f"{base_name}_parameters_{cond}",
                                     band_name, 'param', settings_dic)
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
                            save_outputs(controller, deepcopy(current_params), f"{base_name}_parameters_{cond}_{event_name}", band_name, 'param', settings_dic)

                            # Update the progress bar and labels
                            global_progress = int(((i * len(bands) + j + 1) / total_steps) * 100)
                            controller.view.progressBar.setValue(global_progress)

        # Exception handling
        except Exception as e:
            error_found = True
            controller._log_message(f"Error preprocessing {file}: {e}", style='error')

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
    new_marks.app_settings['conditions']['no-condition'] = {'desc-name': 'No Condition',
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


def save_outputs(controller, data, base_name, suffix, key, settings_dic):
    """
    Saves outputs to disk according to user selections in the GUI.
    """
    # Save preprocessed signals
    if controller.view.prepsignalsCBox.isChecked() and settings_dic['preprocessing']['apply_preprocessing'] and key == 'prep':
        output_dir = join(controller.view.selected_folder, "Preprocessed_signals")
        makedirs(output_dir, exist_ok=True)
        output_path = join(output_dir, f"{base_name}_preprocessing_{suffix}.mat")
        data.save_to_mat(output_path)
        controller._log_message(f"Preprocessed saved in: {output_path}")

    # Save segmented signals
    if controller.view.segsignalsCBox.isChecked() and key == 'seg':
        output_dir = join(controller.view.selected_folder, "Segmented_signals")
        makedirs(output_dir, exist_ok=True)
        output_path = join(output_dir, f"{base_name}_{suffix}.mat")
        savemat(output_path, {'epochs': data})
        controller._log_message(f"Segmentation saved in: {output_path}")

    # Save computed parameters
    if controller.view.paramsignalsCBox.isChecked() and key == 'param':
        output_dir = join(controller.view.selected_folder, "Signal_parameters")
        makedirs(output_dir, exist_ok=True)
        controller._log_message(f"Parameters: folder ready in {output_dir}")
        output_path = join(output_dir, f"{base_name}_{suffix}.mat")
        savemat(output_path, {'parameters': data})
        controller._log_message(f"Parameters saved in: {output_path}")


#################### PREPROCESSING

def apply_preprocessing_ecg(signal, fs, cfg):
    """
    Apply bandpass, notch filtering, and Common Average Reference (CAR).
    """

    # Baseline correction
    if cfg['baseline']:
        signal = medusa.FIRFilter(cfg['baseline_order'], cfg['baseline_cutoff'], 'highpass',
                                  window=cfg['baseline_win']).fit_transform(signal, fs)
    # Bandpass filter
    if cfg['bandpass']:
        signal = medusa.FIRFilter(cfg['bp_order'], [cfg['bp_min'], cfg['bp_max']], 'bandpass',
                                  window=cfg['bp_win']).fit_transform(signal, fs)

    # Zscore and return
    return zscore(signal, axis=0) if cfg['norm'] else signal


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
        # If PSD is explicitly enabled...
        if explicit_psd:
            # Use user-defined parameters for segmenting and windowing
            segment_psd = cfg['parameters']['psd_segment_pct']
            overlap_psd = cfg['parameters']['psd_overlap_pct']
            window_psd = cfg['parameters']['psd_window']

            # Compute PSD using specified segment and window settings
            fxx, psd = medusa.transforms.power_spectral_density(epochs, fs, segment_psd, overlap_psd, window_psd)
        else:
            # Compute PSD with default settings
            fxx, psd = medusa.transforms.power_spectral_density(epochs, fs)

        # Store PSD values: average across trials if averaging is enabled
        try:
            params[f'psd_{band['name']}'] = np.nanmean(psd, axis=0) \
                if cfg['segmentation']['average'] and epochs.ndim == 3 else psd
            params[f'psd_freqs_{band['name']}'] = fxx
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

        # Define broadband range, as the minimum of the mins and the maximum of the maxs of the selected bands
        min_val = min(band["min"] for band in selected_bands if band["name"] != 'broadband')
        max_val = max(band["max"] for band in selected_bands if band["name"] != 'broadband')

        # Loop through each selected band
        for band in selected_bands:
            if band["name"] != 'broadband':
                # Define band parameters
                band_range = [band["min"], band["max"]]
                # Compute the metric
                val_band = medusa.signal_metrics.band_power.band_power(psd, fs, band_range, 'relative', [min_val, max_val])
                # Average across epochs if required and if multiple epochs are present
                val_band = np.nanmean(val_band, axis=0) if cfg['segmentation']['average'] and epochs.ndim == 3 else val_band
                val.append({"band": band["name"], "value": val_band})

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
    for name, func in nonlinear_funcs.items():
        # If selected...
        if cfg['parameters'][name]:
            # Compute it
            val = func()
            # Average across epochs if required and if multiple epochs are present
            val = np.nanmean(val, axis=0) if cfg['segmentation']['average'] and epochs.ndim == 3 else val
            params[f"{name}"] = val

    return params