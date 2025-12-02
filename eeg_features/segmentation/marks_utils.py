import numpy as np
from medusa import components


def extract_condition_events(files):
    """
    Extract conditions and events from a list of files.
    """



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
    """
    Convert the conditions and events from a Recording object to standard dictionaries
    """
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

