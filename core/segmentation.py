
def segment_by_condition(data, current_signal, settings, base_name, norm, band, save_fn, compute_fn):
    import medusa.artifact_removal
    import numpy as np
    from core.utils import get_condition_indices, find_nearest_index
    fs = data.eeg.fs
    fs_seg = fs / 1000
    trial_len = int(settings['segmentation']['trial_length']) * fs_seg
    norm_type = settings['segmentation']['norm_type'] if norm else None
    t_window = [0, int(settings['segmentation']['trial_length'])]
    selected_conditions = settings['segmentation']['selected_conditions']
    thresholding = settings['segmentation']["thresholding"]
    resample = settings['segmentation']['resample']
    resample_fs = settings['segmentation']['resample_fs']
    thres_k = settings['segmentation']['thres_k']
    thres_samples = settings['segmentation']["thres_samples"]
    thres_channels = settings['segmentation']["thres_channels"]

    for cond in selected_conditions:
        if cond == 'null':
            epoched = medusa.get_epochs(current_signal, trial_len, norm=norm_type)
        else:
            cond_key = data.marks.app_settings['conditions'][cond]['label']
            idx = get_condition_indices(data, cond_key)
            if len(idx) % 2 != 0:
                continue

            segments = []
            for i in range(0, len(idx), 2):
                start = find_nearest_index(data.eeg.times, data.marks.conditions_times[idx[i]])
                end = find_nearest_index(data.eeg.times, data.marks.conditions_times[idx[i + 1]])
                segment = current_signal[start:end]
                epochs = medusa.get_epochs(segment, trial_len, norm=norm_type)
                if epochs is not None:
                    segments.append(epochs)

            epoched = np.concatenate(segments, axis=0) if segments else None

            if epoched is not None and thresholding:
                _, epoched, _ = medusa.artifact_removal.reject_noisy_epochs(
                    epoched,
                    np.nanmean(current_signal, axis=0),
                    np.std(current_signal, axis=0),
                    k=thres_k,
                    n_samp=thres_samples,
                    n_cha=thres_channels
                )

            if epoched is not None and resample:
                epoched = medusa.resample_epochs(epoched, t_window, resample_fs)

        if epoched is not None:
            save_fn(epoched, f"{base_name}_segmentation_{cond}", band or 'broadband', 'seg')
            params = compute_fn(epoched, settings, fs, band)
            save_fn(params, f"{base_name}_parameters_{cond}", band or 'broadband', 'param')


def segment_by_event(data, current_signal, settings, base_name, norm, fs, band, save_fn, compute_fn):
    import medusa.artifact_removal
    import numpy as np
    from core.utils import get_condition_indices, get_event_indices_in_range, find_nearest_index, \
        find_nearest_index_array

    w_start, w_end = settings['segmentation']['window_start'], settings['segmentation']['window_end']
    window = [w_start, w_end]
    norm_type = settings['segmentation']['norm_type'] if norm else None
    baseline_window = [settings['segmentation']['baseline_start'],
                       settings['segmentation']['baseline_end']] if norm else None
    selected_conditions = settings['segmentation']['selected_conditions']
    selected_events = settings['segmentation']['selected_events']
    thresholding = settings['segmentation']["thresholding"]
    resample = settings['segmentation']['resample']
    resample_fs = settings['segmentation']['resample_fs']
    thres_k = settings['segmentation']['thres_k']
    thres_samples = settings['segmentation']["thres_samples"]
    thres_channels = settings['segmentation']["thres_channels"]

    for cond in selected_conditions:
        for evt in selected_events:
            if cond == 'null':
                epoched = medusa.get_epochs(current_signal, int(settings['segmentation']['trial_length']),
                                            baseline_window, norm=norm_type)
                if epoched is not None:
                    save_fn(epoched, f"{base_name}_segmentation_{cond}_{evt}", band or 'broadband', 'seg')
                    params = compute_fn(epoched, settings, fs, band)
                    save_fn(params, f"{base_name}_parameters_{cond}_{evt}", band or 'broadband', 'param')
                continue

            cond_key = data.marks.app_settings['conditions'][cond]['label']
            evt_key = data.marks.app_settings['events'][evt]['label']
            idx = get_condition_indices(data, cond_key)
            if len(idx) % 2 != 0:
                continue

            segments = []
            for i in range(0, len(idx), 2):
                start_idx = find_nearest_index(data.eeg.times, data.marks.conditions_times[idx[i]])
                end_idx = find_nearest_index(data.eeg.times, data.marks.conditions_times[idx[i + 1]])
                start_time, end_time = data.eeg.times[start_idx], data.eeg.times[end_idx]

                evt_idx = get_event_indices_in_range(data, evt_key, start_time, end_time)
                onsets = np.array(data.marks.events_times)[evt_idx]
                onsets_idx = find_nearest_index_array(data.eeg.times, onsets)

                epochs = medusa.get_epochs_of_events(data.eeg.times, current_signal, onsets_idx, fs, window,
                                                     baseline_window, norm=norm_type)
                if epochs is not None:
                    segments.append(epochs)

            epoched = np.concatenate(segments, axis=0) if segments else None

            if epoched is not None and thresholding:
                _, epoched, _ = medusa.artifact_removal.reject_noisy_epochs(
                    epoched,
                    np.nanmean(current_signal, axis=0),
                    np.std(current_signal, axis=0),
                    k=thres_k,
                    n_samp=thres_samples,
                    n_cha=thres_channels
                )

            if epoched is not None and resample:
                epoched = medusa.resample_epochs(epoched, window, resample_fs)

            if epoched is not None:
                save_fn(epoched, f"{base_name}_segmentation_{cond}_{evt}", band or 'broadband', 'seg')
                params = compute_fn(epoched, settings, fs, band)
                save_fn(params, f"{base_name}_parameters_{cond}_{evt}", band or 'broadband', 'param')