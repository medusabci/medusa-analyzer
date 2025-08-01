from medusa import components
from medusa import get_epochs, get_epochs_of_events
from Segmentation.utils import recording_to_dict
import numpy as np
import pickle as pkl

def do_segementation(files, selected_conditions, selected_events, win, saving_path):

    # Initialize variables...
    segmented_signal = []
    segmented_signal_lbl = []
    for file in files:
        # Initialize variables...
        segmented_signal_tmp = []
        segmented_signal_lbl_tmp = []

        # Load the signal and get the standard dictionary
        rec = components.Recording.load(file)
        signal = rec.eeg.signal
        fs = rec.eeg.fs

        # Standard dict
        times, conditions, events = recording_to_dict(rec)

        # If the segmentation is window-based
        if not selected_events:

            # Epoch length (from ms to samples)
            win_samples = (win / 1000) * fs

            # Remove conditions not selected
            idx_selected_conditions =  [n_cnd for n_cnd, cnd in enumerate(conditions['conditions_names']) if cnd in selected_conditions]
            conditions['conditions_names'] = conditions['conditions_names'][idx_selected_conditions]
            conditions['conditions_times'] = conditions['conditions_times'][idx_selected_conditions]

            # For each condition interval...
            for n_cnd, cnd in enumerate(conditions['conditions_times']):
                interval = np.where(np.logical_and(times >= cnd[0], times <= cnd[1]))[0]
                # Add one additional sample so that we do not have to discard always an epoch
                interval = np.append(interval, interval[-1] + 1)
                current_signal = signal[interval, :]
                # Segment and store the signal
                segmented_signal_tmp.append(get_epochs(current_signal, win_samples))
                # Store the label
                segmented_signal_lbl_tmp.append(rf'{conditions['conditions_names'][n_cnd]} - {win} ms')

        # If the segmentation is event-based
        else:

            # Adapt "win" to get_epochs_of_events()
            if win[0] < 0:
                w_baseline_t = [win[0], 0]
                w_epoch_t = [0, win[1]]
            else:
                w_baseline_t = None
                w_epoch_t = [win[0], win[1]]

            for event in selected_events:
                # Remove events not selected
                idx_event = [n_evt for n_evt, evt in enumerate(events['events_names']) if evt in event]
                times_tmp = events['events_times'][idx_event]
                conditions_tmp = np.array(events['events_condition'])[idx_event]

                # If we have to filter also by condition...
                if selected_conditions:
                    for condition in selected_conditions:
                        idx_selected_conditions = [n_cnd for n_cnd, cnd in enumerate(conditions_tmp['conditions_names']) if cnd in condition]

                        # Segment and store the signal
                        segmented_signal_tmp.append(
                            get_epochs_of_events(times, signal, times_tmp[idx_selected_conditions], fs, w_epoch_t, w_baseline_t=w_baseline_t))
                        # And the label
                        segmented_signal_lbl_tmp.append(rf'{event} ({condition}) - {win[0]}-{win[1]} ms')
                else:
                    # Segment and store the signal
                    segmented_signal_tmp.append(
                        get_epochs_of_events(times, signal, times_tmp, fs,w_epoch_t, w_baseline_t=w_baseline_t))
                    # And the label
                    segmented_signal_lbl_tmp.append(rf'{event} - {win[0]}-{win[1]} ms')

        # Store the data in the final variables
        segmented_signal.extend(segmented_signal_tmp)
        segmented_signal_lbl.extend(segmented_signal_lbl_tmp)
        del segmented_signal_tmp, segmented_signal_lbl_tmp

        if saving_path:
            file_name = file.split('/')[-1]
            file_name = file_name.rsplit('.', 1)[0]
            with open(rf'{saving_path}/{file_name}.pkl', 'wb') as f:
                pkl.dump((segmented_signal, segmented_signal_lbl), f)

    return segmented_signal, segmented_signal_lbl