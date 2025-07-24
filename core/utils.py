import numpy as np
import os
from scipy.io import savemat

def find_nearest_index(array, value):
    array = np.array(array)
    idx = (np.abs(array - value)).argmin()
    return idx

def find_nearest_index_array(reference_times, query_times):
    reference_times = np.asarray(reference_times)
    query_times = np.asarray(query_times)

    indices = np.searchsorted(reference_times, query_times)
    indices = np.clip(indices, 1, len(reference_times) - 1)

    left = reference_times[indices - 1]
    right = reference_times[indices]

    closest = np.where(
        np.abs(query_times - left) < np.abs(query_times - right), left, right)
    return closest


def get_condition_indices(data, condition_key):
    return np.where(np.array(data.marks.conditions_labels) == condition_key)[0]


def get_event_indices_in_range(data, event_key, start_time, end_time):
    events_labels = np.array(data.marks.events_labels)
    events_times = np.array(data.marks.events_times)
    return np.where(
        (events_labels == event_key) &
        (events_times >= start_time) &
        (events_times <= end_time)
    )[0]


def save_outputs(data, base_name, suffix, key, output_dir, checkboxes):
    from os.path import join
    from os import makedirs

    if checkboxes.get('prep') and key == 'prep':
        out = join(output_dir, "Preprocessed_signals")
        makedirs(out, exist_ok=True)
        path = join(out, f"{base_name}_preprocessing_{suffix}.mat")
        data.save_to_mat(path)

    if checkboxes.get('seg') and key == 'seg':
        out = join(output_dir, "Segmented_signals")
        makedirs(out, exist_ok=True)
        path = join(out, f"{base_name}_{suffix}.mat")
        savemat(path, {'epochs': data})

    if checkboxes.get('param') and key == 'param':
        out = join(output_dir, "Signal_parameters")
        makedirs(out, exist_ok=True)
        path = join(out, f"{base_name}_{suffix}.mat")
        savemat(path, {'parameters': data})