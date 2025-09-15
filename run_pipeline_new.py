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
from scipy.stats import kurtosis, skew
from scipy.io import savemat

def run_pipeline(view, settings_dic, total_tasks):
    """
    Main pipeline function of the eeg features extraction that executes preprocessing, segmentation, and parameter
    computation for all selected files based on the provided configuration.
    """

    # Get the selected files and associated variables
    selected_files = settings_dic['files'].get('selected_files', [])
    total_files = len(selected_files)
    error_found = False

    # Loop through each selected file
    for i, file in enumerate(selected_files):

        # Logging and GUI updates
        # TODO: Uncomment this, I have commented it for testing purposes
        # view._log_message(f"Processing file: {file}")
        # view.progressLabel.setText(f"Processing: {basename(file)}")
        QtWidgets.QApplication.processEvents()


        # Load data
        data = medusa.components.Recording.load(file)
        # Initialize variables
        name_signal = settings_dic['files']['selected_biosignal']  # ej: "eeg"
        current_signal = getattr(data, name_signal).signal
        current_times = getattr(data, name_signal).times
        current_marks = data.marks # TODO: HANDLE NO-CONDITIONS CASE
        fs = getattr(data, name_signal).fs

        # Ensure consistent sampling frequency
        if fs != settings_dic['preprocessing']['fs']:
            raise Exception("One of the selected signals do not have the same sampling frequency: " + file)

        ## First step: Preprocessing
        processed_signal = current_signal.copy()
        if settings_dic['preprocessing']['apply_preprocessing']:
            processed_signal = apply_preprocessing(processed_signal, fs, settings_dic['preprocessing'])

        ## Second step: Get indices of the thresholding
        if settings_dic['segmentation']["thresholding"]:
            idx_threshold = dict()

            if settings_dic['segmentation']['segmentation_type'] == 'conditions':
                # For each condition selected...
                for cond in settings_dic['segmentation']['selected_conditions']:
                    # Get epochs for the current condition
                    epochs = _get_epochs_from_condition(
                        processed_signal, cond, current_marks, current_times, fs, settings_dic['segmentation'])

                    # Get the thresholding parameters
                    thres_k = settings_dic['segmentation']['thres_k']
                    thres_samples = settings_dic['segmentation']["thres_samples"]
                    thres_channels = settings_dic['segmentation']["thres_channels"]
                    # Get the indices of rejected epochs
                    _, _, idx_reject = medusa.artifact_removal.reject_noisy_epochs(
                        epochs, np.nanmean(current_signal, axis=0), np.std(current_signal, axis=0),
                        k=thres_k, n_samp=thres_samples, n_cha=thres_channels)
                    # Store the rejected indices for the current condition
                    idx_threshold[cond] = idx_reject
                    del epochs # Free memory
                else: # segmentation_type == 'events'

                    # Iterate over all conditions and events
                    for cond in settings_dic['segmentation']['selected_conditions']:
                        for evt in settings_dic['segmentation']['selected_events']:
                            cond_key = data.marks.app_settings['conditions'][cond]['label']
                            evt_key = data.marks.app_settings['events'][evt]['label']
                            idx = get_condition_indices(data, cond_key)

                            # Skip if odd number of indices
                            if len(idx) % 2 != 0:
                                continue

                            segments = []
                            for i in range(0, len(idx), 2):
                                start_idx = _find_nearest_index(current_times, data.marks.conditions_times[idx[i]])
                                end_idx = _find_nearest_index(current_times, data.marks.conditions_times[idx[i + 1]])
                                start_time, end_time = current_times[start_idx], current_times[end_idx]

                                evt_idx = get_event_indices_in_range(data, evt_key, start_time, end_time)
                                onsets = np.array(data.marks.events_times)[evt_idx]
                                onsets_idx = _find_nearest_index(current_times, onsets)

                                epochs = medusa.get_epochs_of_events(current_times, current_signal, onsets_idx, fs,
                                                                     window,
                                                                     baseline_window, norm=norm_type)
                                if epochs is not None:
                                    segments.append(epochs)
































# Preprocessing
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


# Helper functions
def _get_epochs_from_condition(signal, condition, marks, times, fs, cfg):
    """
    Extract epochs from the signal based on specified condition names
    """
    # Get segmentation parameters
    fs_seg = fs / 1000
    trial_len = int(cfg['trial_length']) * fs_seg
    trial_stride_val = cfg['trial_stride']
    trial_stride = (trial_stride_val / 100 * trial_len) if trial_stride_val else None
    norm_type = cfg['norm_type'] if cfg['norm'] else None

    # Get the label (numerical value) associated with the condition name
    cond_key = marks.app_settings['conditions'][condition]['label']
    # Find indices of epochs matching the condition label
    idx = np.where(np.array(marks.conditions_labels) == cond_key)[0]
    # Skip if odd number of indices (requires pairs of start/end)
    if len(idx) % 2 != 0:
        return

    # Segment into epochs
    segments = []
    # For each pair of start/end indices
    for i in range(0, len(idx), 2):
        # Start and end sample indices
        start = _find_nearest_index(times, marks.conditions_times[idx[i]])
        end = _find_nearest_index(times, marks.conditions_times[idx[i + 1]])
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
    reference_times = np.asarray(reference_times)
    query_times = np.atleast_1d(query_times)  # Ensure we always work with an array

    # Find insertion points where query_times would be inserted to keep order
    indices = np.searchsorted(reference_times, query_times)

    # Clip to stay within valid index range
    indices = np.clip(indices, 1, len(reference_times) - 1)

    # Get the left and right neighbors
    left = reference_times[indices - 1]
    right = reference_times[indices]

    # Choose the closest neighbor
    choose_left = np.abs(query_times - left) < np.abs(query_times - right)
    nearest_indices = np.where(choose_left, indices - 1, indices)

    # If the input was a single value, return a single index
    if np.isscalar(query_times) or query_times.shape == (1,):
        return nearest_indices[0]
    return nearest_indices