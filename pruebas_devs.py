import medusa
from run_pipeline_new import run_pipeline
import json
import numpy as np

file = r'D:\MEDUSA\medusa-analyzer\Signals\R3.rec.bson'


with open("settings.json", "r", encoding="utf-8") as f:
    settings = json.load(f)

data = medusa.components.Recording.load(file)



run_pipeline([], settings, 3)


def get_new_marks(marks, times):
    marks.app_settings['conditions']['no-condition'] = {'desc-name': 'No Condition',
                                                             'label': len(data.marks.app_settings['conditions']),
                                                             'shortcut': 'NA'}

    # Get the conditions times and labels
    conditions_times = np.array(marks.conditions_times).reshape(-1, 2)
    conditions_labels = np.array(marks.conditions_labels)

    ## Convert the times to indices of the `times` array
    ranges = []
    # For each condition
    for (start_t, end_t), label in zip(conditions_times, conditions_labels):
        # Get the closest initial and final indices in `times`
        start_idx = np.searchsorted(times, start_t)
        end_idx = np.searchsorted(times, end_t)
        # Append the range
        ranges.append((start_idx, end_idx, label))

    new_label = np.max(conditions_labels) + 1
    ## Add intervals with label "new_label" in the gaps
    final_ranges = []
    prev_end = 0
    # For each range
    for start, end, label in ranges:
        # Check if there is a gap between the previous end and the current start
        if prev_end < start:
            # If so, add a new range with label "new_label"
            final_ranges.append((prev_end, start, new_label))
        # Append the current range
        final_ranges.append((start, end, label))
        # The current end becomes the previous end for the next iteration
        prev_end = end

    ## If there is a gap at the end, add it as a new range
    if prev_end < len(times):
        final_ranges.append((prev_end, len(times), new_label))

    ## Create the new conditions_times and conditions_labels arrays
    new_conditions_times = []
    new_conditions_labels = []
    # For each range in final_ranges
    for start_idx, end_idx, label in final_ranges:
        # Append the start and end times
        new_conditions_times.append([times[start_idx], times[end_idx - 1]]) # We use end_idx - 1 to get the actual end time
        # Append the label twice (start and end)
        new_conditions_labels.append(label)
        new_conditions_labels.append(label)

    new_conditions_times = np.array(new_conditions_times).flatten() # Flatten the array
    new_conditions_labels = np.array(new_conditions_labels)

    return new_conditions_times, new_conditions_labels