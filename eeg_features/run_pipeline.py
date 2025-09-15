from PySide6 import QtCore, QtGui, QtWidgets

def run_pipeline(self, settings_dic, total_tasks):
    """
    Main pipeline function of the eeg features extraction that executes preprocessing, segmentation, and parameter
    computation for all selected files based on the provided configuration.
    """
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

    # -------------------------------------------------------------------------
    # Utility functions
    # -------------------------------------------------------------------------
    def find_nearest_index(array, value):
        """
        For segmentation: Find the index of the array element closest to the given value.
        """
        array = np.array(array)
        idx = (np.abs(array - value)).argmin()
        return idx

    def find_nearest_index_array(reference_times, query_times):
        """
        For segmentations: Find nearest indices of query times relative to reference times.

        Returns:
        ndarray: Array of nearest indices.
        """
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
        """
        Return indices of epochs matching a given condition label.
        """
        return np.where(np.array(data.marks.conditions_labels) == condition_key)[0]

    def get_event_indices_in_range(data, event_key, start_time, end_time):
        """
        Return indices of events that occur within a given time interval.
        """
        events_labels = np.array(data.marks.events_labels)
        events_times = np.array(data.marks.events_times)
        return np.where(
            (events_labels == event_key) &
            (events_times >= start_time) &
            (events_times <= end_time)
        )[0]

    # -------------------------------------------------------------------------
    # Preprocessing
    # -------------------------------------------------------------------------
    def apply_preprocessing(signal, fs, cfg):
        """
        Apply bandpass, notch filtering, and Common Average Reference (CAR).

        Args:
        signal (ndarray): Input biosignal.
        fs (float): Sampling frequency.
        cfg (dict): Preprocessing configuration.

        Returns:
        ndarray: Preprocessed signal.
        """
        if cfg.get('bandpass') and None not in (cfg.get('bp_min'), cfg.get('bp_max'), cfg.get('bp_order')):
            signal = medusa.FIRFilter(cfg['bp_order'], [cfg['bp_min'], cfg['bp_max']], 'bandpass',
                                      window=cfg['bp_win']).fit_transform(
                signal, fs)
        if cfg.get('notch') and None not in (cfg.get('notch_min'), cfg.get('notch_max'), cfg.get('notch_order')):
            signal = medusa.FIRFilter(cfg['notch_order'], [cfg['notch_min'], cfg['notch_max']],
                                      'bandstop', window=cfg['notch_win']).fit_transform(signal, fs)
        return medusa.car(signal) if cfg.get('car') else signal

    def band_filtering(signal, bp_min, bp_max, fs, cfg):
        """
        Apply band segmentation with a FIR bandpass filter.
        Used when preprocessing is disabled but band-specific segmentation is required.

        Args:
        signal (ndarray): Input signal.
        bp_min (float): Lower cutoff frequency.
        bp_max (float): Upper cutoff frequency.
        fs (float): Sampling frequency.
        cfg (dict): Preprocessing configuration.

        Returns:
        ndarray: Band-segmented signal.
        """
        order = 1000 if cfg.get('bandpass') is False else cfg.get('bp_order')
        win = 'hamming' if cfg.get('bandpass') is False else cfg.get('bp_win')
        bp_filter = medusa.FIRFilter(order, [bp_min, bp_max], 'bandpass', window=win)
        signal = bp_filter.fit_transform(signal, fs)
        return signal

    # -------------------------------------------------------------------------
    # Segmentation by condition
    # -------------------------------------------------------------------------
    def segment_by_condition(data, current_signal, settings, base_name, norm, band):
        """
        Segment data based on conditions (epochs aligned with experimental conditions).
        Includes thresholding, resampling, and normalization.
        """
        # Variable definition
        fs_seg = fs / 1000
        trial_len = int(settings['segmentation']['trial_length']) * fs_seg
        trial_stride_val = settings['segmentation']['trial_stride']
        trial_stride = (trial_stride_val / 100 * trial_len) if trial_stride_val else None
        norm_type = settings['segmentation']['norm_type'] if norm else None
        t_window = [0, int(settings['segmentation']['trial_length'])]
        selected_conditions = settings['segmentation']['selected_conditions']
        thresholding = settings['segmentation']["thresholding"]
        resample = settings['segmentation']['resample']
        resample_fs = settings['segmentation']['resample_fs']
        thres_k = settings['segmentation']['thres_k']
        thres_samples = settings['segmentation']["thres_samples"]
        thres_channels = settings['segmentation']["thres_channels"]

        def save_and_compute(epoched, cond_name):
            """
            Save segmented signals, compute parameters, and save results.
            """
            if epoched is None:
                return
            save_outputs(epoched, f"{base_name}_segmentation_{cond_name}", band or 'broadband', 'seg')
            params = compute_parameters(epoched, settings, fs, band)
            save_outputs(params, f"{base_name}_parameters_{cond_name}", band or 'broadband', 'param')

        # Process each condition
        for cond in selected_conditions:
            if cond == 'no-condition':
                epoched = medusa.get_epochs(current_signal, trial_len, stride=trial_stride, norm=norm_type)
            else:
                cond_key = data.marks.app_settings['conditions'][cond]['label']
                idx = get_condition_indices(data, cond_key)

                # Skip if odd number of indices (requires pairs of start/end)
                if len(idx) % 2 != 0:
                    continue

                # Segment into epochs for each condition
                segments = []
                for i in range(0, len(idx), 2):
                    start = find_nearest_index(data.eeg.times, data.marks.conditions_times[idx[i]])
                    end = find_nearest_index(data.eeg.times, data.marks.conditions_times[idx[i + 1]])
                    segment = current_signal[start:end]
                    epochs = medusa.get_epochs(segment, trial_len, stride=trial_stride, norm=norm_type)
                    if epochs is not None:
                        segments.append(epochs)
                epoched = np.concatenate(segments, axis=0) if segments else None

            # Thresholding to reject noisy epochs
            if epoched is not None and thresholding:
                _, epoched, _ = medusa.artifact_removal.reject_noisy_epochs(
                    epoched,
                    np.nanmean(current_signal, axis=0),
                    np.std(current_signal, axis=0),
                    k=thres_k,
                    n_samp=thres_samples,
                    n_cha=thres_channels
                )

            # Resampling
            if epoched is not None and resample:
                epoched = medusa.resample_epochs(epoched, t_window, resample_fs)

            save_and_compute(epoched, cond)

    # -------------------------------------------------------------------------
    # Segmentation by event
    # -------------------------------------------------------------------------
    def segment_by_event(data, current_signal, settings, base_name, norm, fs, band):
        """
        Segment data based on events (epochs aligned with event markers).
        Includes baseline correction, thresholding, resampling, and normalization.
        """
        # Variable definition
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

        def save_and_compute(epoched, cond, evt):
            """
            Save segmented signals, compute parameters, and save results.
            """
            if epoched is None:
                return
            label = f"{base_name}_segmentation_{cond}_{evt}"
            band_lbl = band or 'broadband'
            save_outputs(epoched, label, band_lbl, 'seg')
            params = compute_parameters(epoched, settings, fs, band)
            save_outputs(params, label, band_lbl, 'param')

        # Iterate over all conditions and events
        for cond in selected_conditions:
            for evt in selected_events:
                if cond == 'no-condition':
                    evt_key = data.marks.app_settings['events'][evt]['label']
                    onsets = np.array(data.marks.events_times)[np.array(data.marks.events_labels) == evt_key]
                    onsets_idx = find_nearest_index_array(data.eeg.times, onsets)
                    epoched = medusa.get_epochs_of_events(data.eeg.times, current_signal, onsets_idx, fs, window,
                                                          baseline_window, norm=norm_type)
                else:
                    cond_key = data.marks.app_settings['conditions'][cond]['label']
                    evt_key = data.marks.app_settings['events'][evt]['label']
                    idx = get_condition_indices(data, cond_key)

                    # Skip if odd number of indices
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

                # Thresholding to reject noisy epochs
                if epoched is not None and thresholding:
                    _, epoched, _ = medusa.artifact_removal.reject_noisy_epochs(
                        epoched,
                        np.nanmean(current_signal, axis=0),
                        np.std(current_signal, axis=0),
                        k=thres_k,
                        n_samp=thres_samples,
                        n_cha=thres_channels
                    )

                # Resampling
                if epoched is not None and resample:
                    epoched = medusa.resample_epochs(epoched, window, resample_fs)

                save_and_compute(epoched, cond, evt)

    # -------------------------------------------------------------------------
    # Parameter computation
    # -------------------------------------------------------------------------
    def compute_parameters(epoched, settings, fs, band):
        """
        Compute statistical, spectral, nonlinear, and connectivity parameters
        from the segmented data.
        """
        params = {}

        # -------------------------------------------------
        # Basic statistics
        # -------------------------------------------------
        stat_funcs = {
            'mean': np.mean,
            'variance': np.var,
            'median': np.median,
            'kurtosis': kurtosis,
            'skewness': skew
        }
        axis = 0 if epoched.ndim == 2 else 1
        avg = settings['segmentation']['average']
        for name, func in stat_funcs.items():
            if settings['parameters'].get(name, False):
                val = func(epoched, axis=axis)
                params[name] = np.mean(val, axis=0) if avg and epoched.ndim == 3 else val

        # -------------------------------------------------
        # Power Spectral Density (PSD)
        # -------------------------------------------------
        # Check if PSD calculation is explicitly enabled or needed for other metrics
        psd_enabled = settings['parameters'].get('psd', False)

        # Some metrics require PSD even if PSD itself is not explicitly enabled
        needs_psd = any([
            settings['parameters'].get(k, False)
            for k in ['absolute_power', 'median_frequency', 'spectral_entropy']
        ])

        # Determine if we need to compute PSD
        should_compute_psd = psd_enabled or needs_psd

        if should_compute_psd:
            # If PSD is explicitly enabled, use user-defined parameters for segmenting and windowing
            if psd_enabled:
                segment_pct, overlap_pct, window = (
                    settings['parameters']['psd_segment_pct'],
                    settings['parameters']['psd_overlap_pct'],
                    settings['parameters']['psd_window']
                )
                # Compute PSD using specified segment and window settings
                fxx_band, psd_band = medusa.transforms.power_spectral_density(epoched, fs, segment_pct, overlap_pct,
                                                                              window)
            else:
                # Compute PSD with default settings if PSD is needed for other metrics
                fxx_band, psd_band = medusa.transforms.power_spectral_density(epoched, fs)

            # Label the current band (e.g., "alpha", "beta") or default to "broadband"
            band_label = band if band is not None else "broadband"
            # Store PSD values: average across trials if averaging is enabled
            params[f'psd_{band_label}'] = np.nanmean(psd_band, axis=0) if avg else psd_band
            params[f'psd_freq_{band_label}'] = fxx_band

        # --- PSD for broadband (used for relative power) ---
        if settings['parameters'].get('relative_power', False):
            # Define broadband frequency range
            bb = [settings['preprocessing']['broadband_min'], settings['preprocessing']['broadband_max']]

            # Compute PSD for broadband (respecting PSD settings)
            if psd_enabled:
                segment_pct, overlap_pct, window = (
                    settings['parameters']['psd_segment_pct'],
                    settings['parameters']['psd_overlap_pct'],
                    settings['parameters']['psd_window']
                )
                fxx_bb, psd_bb = medusa.transforms.power_spectral_density(epoched, fs, segment_pct, overlap_pct, window)
            else:
                fxx_bb, psd_bb = medusa.transforms.power_spectral_density(epoched, fs)

            # Normalize PSD across broadband range to compute relative power later

            norm_psd = medusa.transforms.normalize_psd(psd_bb, bb, fxx_bb, norm='rel')
            # Save broadband PSD and normalized PSD if the current band is broadband or not specified
            if band == 'broadband' or band is None:
                params['norm_psd_broadband'] = norm_psd
                params['psd_broadband'] = psd_bb
                params['psd_freq_broadband'] = fxx_bb

            # -------------------------------------------------
            # Spectral metrics: relative power
            # -------------------------------------------------
            if settings['preprocessing'].get('band_segmentation', False):
                # Case 1: Band filtering was applied during preprocessing
                # Use the specific frequency bands defined by the user
                selected_bands = settings['preprocessing'].get('selected_bands')
                band_info = next((b for b in selected_bands if b.get("name") == band), None)
                band_range = [band_info.get("min"), band_info.get("max")]
                band_label = band
                val = medusa.signal_metrics.band_power.band_power(norm_psd, fs, band_range)
                params[f"relative_power_{band_label}"] = np.nanmean(val, axis=0) if avg else val
            else:
                # Case 2: No band filtering was applied
                # Use user-selected relative power bands (from parameters)
                selected_rp_bands = settings['parameters'].get('selected_rp_bands', [])

                for band_info in selected_rp_bands:
                    band_range = [band_info.get("min"), band_info.get("max")]
                    band_label = band_info.get("name")
                    val = medusa.signal_metrics.band_power.band_power(norm_psd, fs, band_range)
                    # Average across trials if enabled
                    params[f"relative_power_{band_label}"] = np.nanmean(val, axis=0) if avg else val

        # -------------------------------------------------
        # Spectral metrics: absolute power, median frequency, spectral entropy
        # -------------------------------------------------
        metrics = {
            "absolute_power": medusa.signal_metrics.band_power.band_power,
            "median_frequency": medusa.signal_metrics.median_frequency.median_frequency,
            "spectral_entropy": medusa.signal_metrics.shannon_spectral_entropy.shannon_spectral_entropy,
        }

        for metric_name, metric_func in metrics.items():
            if settings['parameters'].get(metric_name, False):
                if band is None or band == 'broadband':
                    band_range = [
                        settings['preprocessing']['broadband_min'],
                        settings['preprocessing']['broadband_max']
                    ]
                    band_label = "broadband"
                else:
                    selected_bands = settings['preprocessing'].get('selected_bands')
                    band_info = next((b for b in selected_bands if b.get("name") == band), None)
                    band_range = [band_info.get("min"), band_info.get("max")]
                    band_label = band

                val = metric_func(psd_band, fs, band_range)
                params[f"{metric_name}_{band_label}"] = np.nanmean(val, axis=0) if avg else val

        # -------------------------------------------------
        # Non-linear parameters and connectivity metrics
        # -------------------------------------------------
        param_map = {
            'ctm': lambda: medusa.signal_metrics.central_tendency.central_tendency_measure(epoched,
                                                                                           settings['parameters'][
                                                                                               'ctm_r']),
            'sample_entropy': lambda: medusa.signal_metrics.sample_entropy.sample_entropy(epoched,
                                                                                          settings['parameters'][
                                                                                              'sample_entropy_m'],
                                                                                          settings['parameters'][
                                                                                              'sample_entropy_r']),
            'multiscale_sample_entropy': lambda: medusa.signal_metrics.multiscale_entropy.multiscale_entropy(
                epoched, settings['parameters']['multiscale_sample_entropy_scale'],
                settings['parameters']['multiscale_sample_entropy_m'],
                settings['parameters']['multiscale_sample_entropy_r']),
            'lzc': lambda: medusa.signal_metrics.lempelziv_complexity.lempelziv_complexity(epoched),
            'multiscale_lzc': lambda: medusa.signal_metrics.multiscale_lempelziv_complexity.multiscale_lempelziv_complexity(
                epoched,
                settings['parameters']['multiscale_lzc_scales']),
            'iac': lambda: medusa.connectivity_metrics.iac(epoched, settings['parameters']['ort_iac']),
            'aec': lambda: medusa.connectivity_metrics.aec(epoched, settings['parameters']['ort_aec']),
            'plv': lambda: medusa.connectivity_metrics.plv(epoched),
            'pli': lambda: medusa.connectivity_metrics.pli(epoched),
            'wpli': lambda: medusa.connectivity_metrics.wpli(epoched),
        }

        for name, func in param_map.items():
            if settings['parameters'].get(name, False):
                val = func()
                params[name] = np.nanmean(val, axis=0) if avg else val

        return params

    def save_outputs(data, base_name, suffix, key):
        """
        Saves outputs to disk according to user selections in the GUI.
        """
        # ------------------------------
        # Save preprocessed signals
        # ------------------------------
        if self.view.prepsignalsCBox.isChecked() and settings_dic['preprocessing'].get(
                'apply_preprocessing') and key == 'prep':
            output_dir = join(self.view.selected_folder, "Preprocessed_signals")
            makedirs(output_dir, exist_ok=True)
            output_path = join(output_dir, f"{base_name}_preprocessing_{suffix}.mat")
            data.save_to_mat(output_path)
            self.log_message(f"Preprocessed saved in: {output_path}")

        # ------------------------------
        # Save segmented signals
        # ------------------------------
        if self.view.segsignalsCBox.isChecked() and key == 'seg':
            output_dir = join(self.view.selected_folder, "Segmented_signals")
            makedirs(output_dir, exist_ok=True)
            output_path = join(output_dir, f"{base_name}_{suffix}.mat")
            savemat(output_path, {'epochs': data})
            self.log_message(f"Segmentation saved in: {output_path}")

        # ------------------------------
        # Save computed parameters
        # ------------------------------
        if self.view.paramsignalsCBox.isChecked() and key == 'param':
            output_dir = join(self.view.selected_folder, "Signal_parameters")
            makedirs(output_dir, exist_ok=True)
            self.log_message(f"Parameters: folder ready in {output_dir}")
            output_path = join(output_dir, f"{base_name}_{suffix}.mat")
            savemat(output_path, {'parameters': data})
            self.log_message(f"Parameters saved in: {output_path}")

    # ------------------------------
    # Main pipeline execution
    # ------------------------------
    selected_files = settings_dic['files'].get('selected_files', [])
    total_files = len(selected_files)
    error_found = False

    # Loop through each selected file
    for i, file in enumerate(selected_files):
        try:
            # ------------------------------
            # Logging and GUI updates
            # ------------------------------
            self.log_message(f"Processing file: {file}")
            self.view.progressLabel.setText(f"Processing: {basename(file)}")
            QtWidgets.QApplication.processEvents()

            # ------------------------------
            # Load data and initialize variables
            # ------------------------------
            base_name = splitext(basename(file))[0]
            data = medusa.components.Recording.load(file)
            name_signal = settings_dic['files']['selected_biosignal']  # ej: "eeg"
            current_signal = getattr(data, name_signal).signal
            fs = getattr(data, name_signal).fs

            # Ensure consistent sampling frequency
            if fs != settings_dic['preprocessing']['fs']:
                raise Exception("One of the selected signals do not have the same sampling frequency: " + file)

            # Check preprocessing options
            band_seg = settings_dic['preprocessing'].get('band_segmentation', False)  #
            segmentation_type = settings_dic['segmentation']['segmentation_type']
            norm = settings_dic['segmentation']['norm'] or None

            # Determine frequency bands to process
            bands = settings_dic['preprocessing'].get('selected_bands', []) if band_seg else [
                {'name': 'broadband', 'min': settings_dic['preprocessing']['broadband_min'],
                 'max': settings_dic['preprocessing']['broadband_max']}]
            total_steps = total_files * len(bands)

            # ------------------------------
            # Process each frequency band
            # ------------------------------
            for j, band in enumerate(bands):
                band_name = band.get('name', 'unknown')
                bp_min, bp_max = band.get('min'), band.get('max')

                # Avoid Nyquist frequency boundary
                if bp_max == settings_dic['preprocessing']['fs'] / 2:
                    bp_max -= 1e-6
                cfg = {**settings_dic['preprocessing']} # Copy preprocessing configuration

                # ------------------------------
                # Apply preprocessing if enabled
                # ------------------------------
                if settings_dic['preprocessing'].get('apply_preprocessing'):
                    if band_seg:
                        cfg.update({'bp_min': bp_min, 'bp_max': bp_max})
                        signal_to_process = current_signal.copy()
                    else:
                        signal_to_process = current_signal

                    processed_signal = apply_preprocessing(signal_to_process, fs, cfg)
                    data.eeg.signal = processed_signal
                    save_outputs(deepcopy(data), base_name, band_name, 'prep')

                else:  # If no preprocessing, apply only the band segmentation (if apply)
                    if band_seg:
                        processed_signal = band_filtering(current_signal.copy(), bp_min, bp_max, fs, cfg)
                        data.eeg.signal = processed_signal
                    else:
                        processed_signal = current_signal

                # ------------------------------
                # Segment data and compute parameters
                # ------------------------------
                if segmentation_type == 'condition':
                    segment_by_condition(data, processed_signal, settings_dic, base_name, norm,
                                         band=band_name if band_seg else None)
                elif segmentation_type == 'event':
                    segment_by_event(data, processed_signal, settings_dic, base_name, norm, fs,
                                     band=band_name if band_seg else None)

                # Update the progress bar and labels
                global_progress = int(((i * len(bands) + j + 1) / total_steps) * 100)
                self.view.progressBar.setValue(global_progress)

        # ------------------------------
        # Exception handling
        # ------------------------------
        except Exception as e:
            error_found = True
            self.log_message(f"Error preprocessing {file}: {e}", style='error')
    return not error_found