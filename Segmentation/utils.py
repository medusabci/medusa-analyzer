import numpy as np
from medusa import components
import medusa.bci.erp_spellers
import medusa.ecg

def find_valid_conditions(vector):
    """
    Find the index of the init of all the valid conditions

    Args:
        vector (list or array): numerical vector

    Returns:
        list: Indices of valid conditions
    """
    indices = []
    i = 0
    while i < len(vector) - 1:
        if vector[i] == vector[i + 1]:
            indices.append(i)
            i += 2  # The next iteration will be skipped, as it is the end of the current condition
        else:
            i += 1
    return indices


def events_whithin_condition(times, interval):
    """
    Returns the elements of times whithin interval

    Args:
        times (list or array): times
        interval (list or tuple):

    Returns:
        list: elements of times whithin interval
    """
    A, B = interval
    return [times.index(t) for t in times if A <= t <= B]


def remove_consecutive_duplicates(arr):
    """
    Remove consecutive duplicate elements from a list, and return both the filtered elements
    and their original indices.

    Parameters:
    arr (list): The input list from which consecutive duplicates will be removed.

    Returns:
    tuple: A tuple (elements, indices), where:
        - elements is a list of the filtered elements.
        - indices is a list of the positions in the original list where those elements occurred.

    Example:
    >>> remove_consecutive_duplicates([1, 1, 2, 2, 2, 3, 1, 1, 4, 4, 5])
    ([1, 2, 3, 1, 4, 5], [0, 2, 5, 6, 8, 10])
    """
    if not arr:
        return [], []

    elements = [arr[0]]
    indices = [0]

    for idx, item in enumerate(arr[1:], start=1):
        if item != elements[-1]:
            elements.append(item)
            indices.append(idx)

    return elements, indices


def remove_key(obj, key_to_remove):
    """
    Recursively removes all keys named 'key_to_remove' from a nested data structure.

    This function traverses dictionaries, lists, and tuples at any depth and
    removes any occurrence of the key 'key_to_remove' from dictionaries. The modification
    is done in-place.

    Parameters:
    obj (any): A Python object, typically a dictionary, list, or tuple, potentially
               containing nested dictionaries with 'key_to_remove' keys.

    Returns:
    None: The input object is modified in-place. Nothing is returned.

    Example:
    >>> data = {'a': {'times': [1, 2], 'b': [{'times': [3, 4]}]}}
    >>> remove_times_key(data, 'times')
    >>> print(data)
    {'a': {'b': [{}]}}
    """
    if isinstance(obj, dict):
        obj.pop(key_to_remove, None)  # safely remove 'times' key if present
        for key, value in obj.items():
            remove_key(value, key_to_remove)
    elif isinstance(obj, list) or isinstance(obj, tuple):
        for item in obj:
            remove_key(item, key_to_remove)
    return obj


def merge_segmentation_dict(segmentation_dict, group_segmentation_dict=None):
    """
    Merge segmentation dictionaries to create a group-wise segmentation dictionary.

    Parameters:
    segmentation_dict (dict): subject-wise segmentation dictionary.
    group_segmentation_dict (dict): group-wise segmentation dictionary, that will be accumulating all the info

    Returns:
    group_segmentation_dict (dict):
    """
    # Remove the time information
    segmentation_dict = remove_key(segmentation_dict, 'times')

    # If there is no group dict, the subject-wise dict will be stored as is
    if group_segmentation_dict is None:
        group_segmentation_dict = segmentation_dict
    else:
        for key in segmentation_dict.keys():
            # If a condition (included in the subject-wise dict) is not in the group dict, include it
            if key not in group_segmentation_dict:
                group_segmentation_dict[key] = segmentation_dict[key]
            else:
                for event in segmentation_dict[key]['events'].keys():
                    # If a event (included in the subject-wise dict) is not in the group dict, include it
                    if event not in group_segmentation_dict[key]['events']:
                        group_segmentation_dict[key]['events'][event] = {}

    return group_segmentation_dict


def extract_condition_events(files):
    conditions = []
    events = []
    events_condition = []
    for file in files:
        rec = components.Recording.load(file)

        if not hasattr(rec, "marks"):
            # Empty marks
            marks = components.CustomExperimentData()
            marks.events_labels = []
            marks.events_times = []
            marks.conditions_labels = []
            marks.conditions_times = np.empty((0, 2))
            rec.add_experiment_data(marks, key='marks')
            rec.marks.app_settings = {}
            rec.marks.app_settings['conditions'] = {}
            rec.marks.app_settings['events'] = {}

        # Standard dict
        _, conditions_tmp, events_tmp = recording_to_dict(rec)
        conditions.extend(conditions_tmp['conditions_names'])
        events.extend(events_tmp['events_names'])
        events_condition.extend(events_tmp['events_condition'])

    return conditions, events, events_condition


def recording_to_dict(rec):
    times = rec.eeg.times - rec.eeg.times[0]

    # Vector to transform numeric labels to standard names, and array with the names
    label_to_conditions = {info['label']: name for name, info in rec.marks.app_settings['conditions'].items()}
    conditions_names = [label_to_conditions[label] for label in rec.marks.conditions_labels[0::2]]

    # Numeric matrix with the conditions
    # Detect if the last condition is not finished
    if len(rec.marks.conditions_labels) % 2 != 0 and (rec.marks.conditions_labels[-1] != rec.marks.conditions_labels[-2]):
        rec.marks.conditions_labels.append(rec.marks.conditions_labels[-1])
        rec.marks.conditions_times.append(rec.eeg.times[-1])
    conditions_times = rec.marks.conditions_times - rec.eeg.times[0]
    conditions_times = np.reshape(conditions_times, (-1, 2))

    # Get the intervals for the null condition
    null_times = get_null_condition_times(conditions_times, [0, rec.eeg.times[-1] - rec.eeg.times[0]])
    if null_times.size > 0:
        if null_times.ndim == 1:
            null_times = null_times.reshape(1, -1)
        conditions_names.extend(['no-condition'] * len(null_times))
        conditions_times = np.concatenate((conditions_times, null_times), axis=0)
    sort_idx = np.argsort(conditions_times[:, 0])
    conditions_times = conditions_times[sort_idx]
    conditions_names = np.array(conditions_names)[sort_idx]

    # Standard dictionary for the conditions
    conditions = {
        'conditions_names': conditions_names,
        'conditions_times': conditions_times,
        'conditions_labels': rec.marks.conditions_labels[0::2],
        'names_to_labels': label_to_conditions
    }

    label_to_event = {info['label']: name for name, info in rec.marks.app_settings['events'].items()}
    event_names = [label_to_event[label] for label in rec.marks.events_labels]
    events_times = rec.marks.events_times - rec.eeg.times[0]
    condition_event = np.logical_and(events_times >= conditions_times[:, 0][:, None],
                                     events_times <= conditions_times[:, 1][:, None])
    condition_event_str = []
    for event in condition_event.T:
        if not np.any(event):
            condition_event_str.append('no-condition')
        else:
            condition_event_str.append(np.array(conditions['conditions_names'])[event].item())
    condition_event = condition_event_str
    del condition_event_str

    # Standard dictionary for the events
    events = {
        'events_names': event_names,
        'events_times': events_times,
        'events_condition': condition_event,
        'events_labels': rec.marks.events_labels,
        'names_to_labels': label_to_event
    }

    return times, conditions, events


def get_null_condition_times(conditions_times, whole_interval):
    """
    Get time intervals that are not covered by any condition.
    If no conditions exist, the entire interval is considered 'no-condition'.
    """
    gaps = []

    if conditions_times.shape[0] == 0:
        return np.array([whole_interval])

    if conditions_times[0][0] > whole_interval[0]:
        gaps.append([whole_interval[0], conditions_times[0][0]])

    for i in range(1, len(conditions_times)):
        prev_end = conditions_times[i - 1][1]
        curr_start = conditions_times[i][0]
        if curr_start > prev_end:
            gaps.append([prev_end, curr_start])

    if conditions_times[-1][1] < whole_interval[1]:
        gaps.append([conditions_times[-1][1], whole_interval[1]])

    return np.array(gaps)

