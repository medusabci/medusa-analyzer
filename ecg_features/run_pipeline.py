from PySide6 import QtCore, QtGui, QtWidgets
import medusa
import medusa.artifact_removal
import medusa.transforms
from medusa.signal_metrics import central_tendency, median_frequency, shannon_spectral_entropy

import numpy as np
from os.path import basename, join, splitext
from os import makedirs
from copy import deepcopy
import neurokit2.ecg as nkecg
from neurokit2 import signal_rate, hrv
from neurokit2.signal import signal_psd

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
    selected_channels = settings_dic['leads']['selected_leads']
    selected_conditions = settings_dic['leads'].get('selected_conditions', []) or ['all']

    error_found = False

    view = controller.view

    # Config of the progress bar
    steps_per_lead = 2 + 4
    steps_per_file = 1 + steps_per_lead * len(settings_dic['leads']['selected_leads'])
    total_steps = total_files * steps_per_file # Total steps for the progress bar

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
            original_signal = np.array(getattr(data, name_signal).signal)
            signal_times = getattr(data, name_signal).times
            channel_set = getattr(data, name_signal).channel_set
            signal_marks = include_no_conditions_in_marks(data.marks, signal_times)
            fs = getattr(data, name_signal).fs

            # Save original data
            save_outputs(controller, deepcopy(data), base_name, f'original', 'prep',
                         settings_dic)
            # Ensure consistent sampling frequency
            if fs != settings_dic['preprocessing']['fs']:
                raise Exception("One of the selected signals do not have the same sampling frequency: " + file)

            # Update the progress bar and labels
            global_progress = (i*steps_per_file + 1) / total_steps * 100
            controller.view.progressBar.setValue(int(global_progress))

            ## First step: Select channels
            for j, chan_name in enumerate(settings_dic['leads']['selected_leads']):
                idx_chan = channel_set['l_cha'].index(chan_name)

                original_signal_chan = deepcopy(original_signal[:, idx_chan])
                original_signal_chan = np.ravel(original_signal_chan)

                ## Second step: Preprocessing ECG
                processed_signal = deepcopy(original_signal_chan)
                if settings_dic['preprocessing']['clean'] or settings_dic['preprocessing']['zscore']:
                    processed_signal = clean_zscore_ecg(processed_signal, fs, settings_dic['preprocessing'])

                # Update the progress bar and labels
                global_progress = (i * steps_per_file + 1 + j * steps_per_lead + 1) / total_steps * 100
                controller.view.progressBar.setValue(int(global_progress))

                ## Third step: Separate by condition
                segments = []
                conditions = []
                if settings_dic['leads']['selected_conditions']:
                    for cond in settings_dic['segmentation']['selected_conditions']:
                        segments.append(get_epochs_from_condition(processed_signal, cond, signal_marks, signal_times, fs))
                        conditions.append(cond)
                else:
                    segments.append(deepcopy(processed_signal))
                    conditions.append('all')

                # Update the progress bar and labels
                global_progress = (i * steps_per_file + 1 + j * steps_per_lead + 2) / total_steps * 100
                controller.view.progressBar.setValue(int(global_progress))

                # For each segment (condition)...
                for segment_idx, segment in enumerate(segments):

                    cond = conditions[segment_idx]

                    save_outputs(controller, deepcopy(segment), base_name, f'ecg_{cond}_{chan_name}', 'prep', settings_dic)
                    ## Fourth step: HRV computation
                    if settings_dic['preprocessing']['hrv']:
                        method = settings_dic['preprocessing']['processing_method']
                        correction = settings_dic['preprocessing']['correct_artifacts']
                        peaks, _ = nkecg.ecg_peaks(segment, sampling_rate=fs, method=method, correct_artifacts=correction)
                        pulse_rate = signal_rate(peaks, sampling_rate=fs)
                        hrv_signal = np.divide(60,pulse_rate) * 1000 # In ms

                        ## Fifth step: Resample HRV
                        fs_hrv = settings_dic['preprocessing']['resample_fs']
                        t_hrv = np.cumsum(hrv_signal)
                        t_uniform = np.arange(0, t_hrv[-1], 1/fs_hrv)
                        hrv_signal = np.interp(t_uniform, t_hrv, hrv_signal)
                        save_outputs(controller, deepcopy(hrv_signal), base_name, f'hrv_{cond}_{chan_name}', 'prep',
                                     settings_dic)

                        ## Fifth step: Save outputs
                        params = compute_parameters_hrv(peaks, hrv_signal, fs, fs_hrv, settings_dic['parameters'])
                        save_outputs(controller, deepcopy(params), base_name, f'hrv_params_{cond}_{chan_name}', 'param',
                                     settings_dic)

                # Update the progress bar and labels
                global_progress = (i * steps_per_file + 1 + j * steps_per_lead + 6) / total_steps * 100
                controller.view.progressBar.setValue(int(global_progress))

            view.progressLabel.setText("Completed")
        # Exception handling
        except Exception as e:
            error_found = True
            controller._log_message(f"Error preprocessing {file}: {e}", style='error')
            view.progressLabel.setText("Error")

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


def get_epochs_from_condition(signal, condition, marks, times, fs):
    """
    Extract epochs from the signal based on specified condition names
    """
    # Get the label (numerical value) associated with the condition name
    cond_key = marks.app_settings['conditions'][condition]['label']

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
        # Extract segment
        segment = signal[start:end]
        # Get epochs from the segment
        epochs = medusa.get_epochs(segment, segment.shape[0])

        # Append if epochs were created
        if epochs is not None:
            segments.append(epochs)

    return segments
def _find_nearest_index(reference_times, query_times):
    """
    Find the index (or indices) in reference_times closest to query_times.
    """
    # References times is the times vector
    reference_times = np.asarray(reference_times)
    # Query times is the markers of the conditions
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
    if controller.view.prepsignalsCBox.isChecked() and (settings_dic['preprocessing']['clean'] or settings_dic['preprocessing']['zscore']) and key == 'prep':
        output_dir = join(controller.view.selected_folder, "Preprocessed_signals")
        makedirs(output_dir, exist_ok=True)
        output_path = join(output_dir, f"{base_name}_preprocessing_{suffix}.mat")
        if suffix == 'original':
            data.save_to_mat(output_path)
        else:
            savemat(output_path, {suffix: data})
        controller._log_message(f"Preprocessed saved in: {output_path}")

    # Save computed parameters
    if controller.view.paramsignalsCBox.isChecked() and key == 'param':
        output_dir = join(controller.view.selected_folder, "Signal_parameters")
        makedirs(output_dir, exist_ok=True)
        controller._log_message(f"Parameters: folder ready in {output_dir}")
        output_path = join(output_dir, f"{base_name}_{suffix}.mat")
        savemat(output_path, {'parameters': data})
        controller._log_message(f"Parameters saved in: {output_path}")


#################### PREPROCESSING

def clean_zscore_ecg(signal, fs, cfg):
    """
    Apply bandpass, notch filtering, and Common Average Reference (CAR).
    """

    # Baseline correction
    if cfg['clean']:
        signal = nkecg.ecg_clean(signal, sampling_rate=fs, method=cfg['clean_method'])

    # Zscore and return
    return zscore(signal, axis=0) if cfg['zscore'] else signal


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

def compute_parameters_hrv(peaks, hrv_signal, fs, fs_hrv, cfg):

    # Initialize dict that will contain all the computed parameters
    params = {}

    # Get the parameters provided by neurokit2
    params_nk = hrv(peaks, sampling_rate=fs)

    # TIME METRICS
    time_funcs = {
        'pulse_rate': '',
        'averege': 'MeanNN',
        'std_nn': 'SDNN',
        'rms_sucessive_diff': 'RMSSD',
        'std_sucessive_diff': 'SDSD',
        'variation_coef': 'CVNN',
        'tring_interp': 'TINN',
        'pnn20': 'pNN20',
        'pnn50': 'pNN50'}

    # For each parameter...
    for name, name_nk in time_funcs.items():
        try:
            # If selected...
            if cfg[name]:
                # Store in the params dict
                if name == 'pulse_rate':
                    params[f"{name}"] = signal_rate(peaks, sampling_rate=fs)
                else:
                    params[f"{name}"] = params_nk['HRV_' + name_nk][0]
        except Exception:
            params[f"{name}"] = np.nan


    # SPECTRAL METRICS

    # Compute PSD
    try:
        psd = signal_psd(peaks['ECG_R_Peaks'].to_numpy(), sampling_rate=fs_hrv, max_frequency=0.55, window_type="hann", order=16)
    except Exception:
        psd = None

    spectral_funcs = {
        'psd': psd,
        'sympathovagal_balance': params_nk['HRV_LFHF'][0],
    }
    # For each parameter...
    for name, name_nk in spectral_funcs.items():
        # If selected...
        if cfg[name]:
            try:
                # Store in the params dict
                params[f"{name}"] = name_nk
            except Exception:
                params[f"{name}"] = np.nan

    spectral_funcs_bands = {
        'power': '',
        'median_frequency': lambda band: medusa.signal_metrics.median_frequency.median_frequency(psd['Power'].to_numpy()[np.newaxis, ..., np.newaxis], fs_hrv, [band['min'], band['max']]),
        'spectral_entropy': lambda band: medusa.signal_metrics.shannon_spectral_entropy.shannon_spectral_entropy(psd['Power'].to_numpy()[np.newaxis, ..., np.newaxis], fs_hrv, [band['min'], band['max']]),
        'kurtosis': lambda _: float(kurtosis(peaks, axis=0)),
        'skewness': lambda _: float(skew(peaks, axis=0)),
    }
    if cfg['selected_bands'] is not None:
        for band in cfg['selected_bands']:
            band_name = 'TP' if band['name'] == 'Broadband' else band['name']
            # For each parameter...
            for name, func in spectral_funcs_bands.items():
                # If selected...
                if cfg[name]:
                    try:
                        if name == 'power':
                            params[f"{name}_{band_name}"] = params_nk[f'HRV_{band_name}'][0]
                        else:
                            # Store in the params dict
                            params[f"{name}_{band_name}"] = func(band)
                    except Exception:
                        params[f"{name}_{band_name}"] = np.nan

    # NONLINEAR METRICS
    nonlinear_funcs = {
        'ctm': lambda: np.ravel(medusa.signal_metrics.central_tendency.central_tendency_measure(np.expand_dims(hrv_signal, axis=(0, 2)),cfg['ctm_r'])),
        'sample_entropy': ['SampEn'],
        'shannon_entropy': ['ShanEn'],
        'lzc': ['LZC'],
        "dfa": ['DFA_alpha1', 'DFA_alpha2'],
        "poincare": ['SD1', 'SD2', 'SD1SD2', 'S']
    }

    # For each parameter...
    for name, name_nk_func in nonlinear_funcs.items():
        # If selected...
        if cfg[name]:
            try:
                if name == 'ctm':
                    params[f"{name}"] = name_nk_func()
                elif len(name_nk_func) > 1:
                    for subname in name_nk_func:
                        params[f"{subname}"] = params_nk['HRV_' + subname][0]
                else:
                    # Store in the params dict
                    params[f"{name}"] = params_nk['HRV_' + name_nk_func[0]][0]
            except Exception:
                if name == 'ctm':
                    params[name] = np.nan
                elif len(name_nk_func) > 1:
                    for subname in name_nk_func:
                        params[subname] = np.nan
                else:
                    params[name] = np.nan

    return params
