import os
import json
from PyQt5 import QtWidgets, uic
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QApplication

class DownloadWidget(QtWidgets.QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        uic.loadUi("final_window.ui", self)

        self.selectfolderButton = self.findChild(QtWidgets.QPushButton, "selectfolderButton")
        self.selectfolderLabel = self.findChild(QtWidgets.QLabel, "selectfolderLabel")
        self.settingsCBox = self.findChild(QtWidgets.QCheckBox, "settingsCBox")
        self.prepsignalsCBox = self.findChild(QtWidgets.QCheckBox, "prepsignalsCBox")
        self.segsignalsCBox = self.findChild(QtWidgets.QCheckBox, "segsignalsCBox")
        self.paramsignalsCBox = self.findChild(QtWidgets.QCheckBox, "paramsignalsCBox")
        self.runButton = self.findChild(QtWidgets.QPushButton, "runButton")
        self.progressLabel = self.findChild(QtWidgets.QLabel, "progressLabel")
        self.progressBar = self.findChild(QtWidgets.QProgressBar, "progressBar")
        self.logtextBrowser = self.findChild(QtWidgets.QTextBrowser, "logtextBrowser")
        self.settings = {}

        # Estados
        self.progressLabel.hide()
        self.progressBar.hide()
        self.selected_folder = None
        for w in [self.settingsCBox, self.prepsignalsCBox, self.segsignalsCBox, self.paramsignalsCBox]:
            w.setChecked(True)

        # Connect button
        self.selectfolderButton.clicked.connect(self.select_folder)
        self.runButton.clicked.connect(self.run_tasks)

    def handle_exception(func):
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                if hasattr(self, 'log_message'):
                    self.log_message(f"[ERROR] {func.__name__}: {str(e)}", style='error')
                else:
                    print(f"[ERROR] {func.__name__}: {str(e)}")

        return wrapper

    def prepare_data(self, preprocessing, segmentation, parameters):
        self.settings_dic = {
            "preprocessing": preprocessing,
            "segmentation": segmentation,
            "parameters": parameters
        }

        self.json_path = os.path.join(self.selected_folder, "settings.json")

        try:
            self.log_message(f"Saving JSON in: {self.json_path}")
            with open(self.json_path, "w") as f:
                json.dump(self.settings_dic, f, indent=4)
        except Exception as e:
            self.log_message(f"ERROR SAVING JSON: {e}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Could not save the JSON file: {str(e)}")

    def select_folder(self, *args, **kwargs):
        while True:
            folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Folder")
            if not folder:
                return  # User cancelled

            if os.listdir(folder):
                QtWidgets.QMessageBox.warning(self, "Error",
                                              "The selected folder is not empty. Please select an empty folder.")
            else:
                self.selected_folder = folder
                self.selectfolderLabel.setText(folder)
                break

    @handle_exception
    def run_tasks(self, *args, **kwargs):
        if not self.selected_folder:
            QtWidgets.QMessageBox.warning(self, "Error", "Please, select one folder to save the data.")
            return

        self.progressLabel.show()
        self.progressBar.show()
        self.progressBar.setValue(0)
        self.error_occurred = False

        total_tasks = sum([
            self.settingsCBox.isChecked(),
            self.prepsignalsCBox.isChecked(),
            self.segsignalsCBox.isChecked(),
            self.paramsignalsCBox.isChecked()
        ])
        total_tasks = max(total_tasks, 1)  # Asegura que nunca sea cero para evitar división por cero

        try:
            preprocessing = self.main_window.preproc_widget.get_preprocessing_config()
            segmentation = self.main_window.segmentation_widget.get_segmentation_config()
            parameters = self.main_window.parameters_widget.get_parameters_config()
        except AttributeError as e:
            QtWidgets.QMessageBox.critical(self, "Error",
                                           f"Unable to obtain the data from the main window: {e}")
            return

        # Guardar settings si está marcado
        if self.settingsCBox.isChecked():
            self.prepare_data(preprocessing, segmentation, parameters)

        # Ejecutar pipeline SIEMPRE
        self.settings_dic = {
            "preprocessing": preprocessing,
            "segmentation": segmentation,
            "parameters": parameters
        }

        success = self.run_pipeline(self.settings_dic, total_tasks)
        self.main_window.validate_download_step(success)

    def log_message(self, msg, style=None):
        # Estilos adaptados para fondo blanco
        theme_colors = {
            'THEME_TEXT_LIGHT': '#333333',  # Texto oscuro para buena legibilidad
            'THEME_RED': '#D32F2F',  # Rojo más profundo
            'THEME_YELLOW': '#FBC02D'  # Amarillo más oscuro
        }
        if isinstance(style, str):
            if style == 'error':
                style = {'color': theme_colors['THEME_RED']}
            elif style == 'warning':
                style = {'color': theme_colors['THEME_YELLOW']}
            else:
                style = {'color': theme_colors['THEME_TEXT_LIGHT']}
        elif style is None:
            style = {'color': theme_colors['THEME_TEXT_LIGHT']}

        style.setdefault('font-size', '9pt')
        style_str = ';'.join(f'{k}: {v}' for k, v in style.items())

        formatted = f'<p style="margin:0;margin-top:2;{style_str}"> >> {msg} </p>'
        self.logtextBrowser.append(formatted)
        self.logtextBrowser.moveCursor(QTextCursor.End)
        QApplication.processEvents()

    def run_pipeline(self, settings_dic, total_tasks):
        import medusa
        import medusa.artifact_removal
        import medusa.transforms
        from medusa.signal_metrics import band_power, median_frequency, shannon_spectral_entropy, central_tendency
        from medusa.signal_metrics import sample_entropy, multiscale_entropy, multiscale_lempelziv_complexity, lempelziv_complexity
        from medusa.connectivity_metrics import iac, aec, plv, pli, wpli
        import numpy as np
        from os.path import basename, join, splitext
        from os import makedirs
        from copy import deepcopy
        from scipy.stats import kurtosis, skew
        from scipy.io import savemat

        selected_files = settings_dic['preprocessing'].get('selected_files', [])
        total_files = len(selected_files)

        def apply_preprocessing(signal, fs, cfg):
            if cfg.get('bandpass') and None not in (cfg.get('bp_min'), cfg.get('bp_max'), cfg.get('bp_order')):
                signal = medusa.FIRFilter(cfg['bp_order'], [cfg['bp_min'], cfg['bp_max']], 'bandpass').fit_transform(
                    signal, fs)
            if cfg.get('notch') and None not in (cfg.get('notch_min'), cfg.get('notch_max'), cfg.get('notch_order')):
                signal = medusa.FIRFilter(cfg['notch_order'], [cfg['notch_min'], cfg['notch_max']],
                                          'bandstop').fit_transform(signal, fs)
            return medusa.car(signal) if cfg.get('car') else signal

        def band_segmentation (signal, bp_min, bp_max, fs):
            bp_filter = medusa.FIRFilter(1000, [bp_min, bp_max], 'bandpass')
            signal = bp_filter.fit_transform(signal, fs)
            return signal

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

        def compute_parameters(epoched, settings, fs, band):
            params = {}

            # --- Estadísticos básicos ---
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

            # --- PSD si es necesario ---
            psd_enabled = settings['parameters'].get('psd', False)
            needs_psd = any([
                settings['parameters'].get(k, False)
                for k in ['relative_power', 'absolute_power', 'median_frequency', 'spectral_entropy']
            ])
            should_compute_psd = psd_enabled or needs_psd
            if should_compute_psd  and (band == 'broadband' or band is None):
                if psd_enabled:
                    segment_pct, overlap_pct, window = (settings['parameters']['psd_segment_pct'], settings['parameters']['psd_overlap_pct'],
                                                        settings['parameters']['psd_window'])
                    fxx, psd = medusa.transforms.power_spectral_density(epoched, fs, segment_pct, overlap_pct, window)
                else:
                    fxx, psd = medusa.transforms.power_spectral_density(epoched, fs)
                params['psd'] = np.nanmean(psd, axis=0) if avg else psd
                params['psd_freq'] = fxx

            # --- Relative Power ---
            if settings['parameters'].get('relative_power', False) and (band == 'broadband' or band is None):
                bb = [settings['parameters']['broadband_min'], settings['parameters']['broadband_max']]
                norm_psd = medusa.transforms.normalize_psd(psd, bb, fxx, norm='rel')
                params['norm_psd'] = norm_psd
                for b in settings['parameters']['selected_rp_bands']:
                    val = medusa.signal_metrics.band_power.band_power(norm_psd, fs, [b['min'], b['max']])
                    params[f"relative_power_{b.get('name', 'unknown')}"] = np.nanmean(val, axis=0) if avg else val

            # --- Absolute Power ---
            if settings['parameters'].get('absolute_power', False) and (band == 'broadband' or band is None):
                for b in settings['parameters']['selected_ap_bands']:
                    val = medusa.signal_metrics.band_power.band_power(psd, fs, [b['min'], b['max']])
                    params[f"absolute_power_{b.get('name', 'unknown')}"] = np.nanmean(val, axis=0) if avg else val

            # --- Median Frequency ---
            if settings['parameters'].get('median_frequency', False) and (band == 'broadband' or band is None):
                for b in settings['parameters']['selected_mf_bands']:
                    val = medusa.signal_metrics.median_frequency.median_frequency(psd, fs, [b['min'], b['max']])
                    params[f"median_frequency_{b.get('name', 'unknown')}"] = np.nanmean(val, axis=0) if avg else val

            # --- Spectral Entropy ---
            if settings['parameters'].get('spectral_entropy', False) and (band == 'broadband' or band is None):
                for b in settings['parameters']['selected_se_bands']:
                    val = medusa.signal_metrics.shannon_spectral_entropy.shannon_spectral_entropy(psd, fs,[b['min'], b['max']])
                    params[f"spectral_entropy_{b.get('name', 'unknown')}"] = np.nanmean(val, axis=0) if avg else val

            # --- Non linear and connectivity parameters ---
            param_map = {
                'ctm': lambda: medusa.signal_metrics.central_tendency.central_tendency_measure(epoched,
                                                                            settings['parameters']['ctm_r']),
                'sample_entropy': lambda: medusa.signal_metrics.sample_entropy.sample_entropy(epoched,
                                                                            settings['parameters']['sample_entropy_m'],
                                                                            settings['parameters']['sample_entropy_r']),
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

        def segment_by_condition(data, current_signal, settings, base_name, norm, band):
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

            def save_and_compute(epoched, cond_name):
                if epoched is None:
                    return
                save_outputs(epoched, f"{base_name}_segmentation_{cond_name}", band or 'broadband', 'seg')
                params = compute_parameters(epoched, settings, fs, band)
                save_outputs(params, f"{base_name}_parameters_{cond_name}", band or 'broadband', 'param')

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

                save_and_compute(epoched, cond)

        def segment_by_event(data, current_signal, settings, base_name, norm, fs, band):
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
                if epoched is None:
                    return
                label = f"{base_name}_segmentation_{cond}_{evt}"
                band_lbl = band or 'broadband'
                save_outputs(epoched, label, band_lbl, 'seg')
                params = compute_parameters(epoched, settings, fs, band)
                save_outputs(params, label, band_lbl, 'param')

            for cond in selected_conditions:
                for evt in selected_events:
                    if cond == 'null':
                        evt_key = data.marks.app_settings['events'][evt]['label']
                        onsets = np.array(data.marks.events_times)[np.array(data.marks.events_labels) == evt_key]
                        onsets_idx = find_nearest_index_array(data.eeg.times, onsets)
                        epoched = medusa.get_epochs_of_events(data.eeg.times, current_signal, onsets_idx, fs, window,
                                                             baseline_window, norm=norm_type)

                        save_and_compute(epoched, cond, evt)
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

                    save_and_compute(epoched, cond, evt)

        def save_outputs(data, base_name, suffix, key):
            """Guarda los archivos según lo seleccionado por el usuario"""
            if self.prepsignalsCBox.isChecked() and settings_dic['preprocessing'].get('apply_preprocessing') and key == 'prep':
                output_dir = join(self.selected_folder, "Preprocessed_signals")
                makedirs(output_dir, exist_ok=True)
                output_path = join(output_dir, f"{base_name}_preprocessing_{suffix}.mat")
                data.save_to_mat(output_path)
                self.log_message(f"Preprocessed saved in: {output_path}")

            if self.segsignalsCBox.isChecked() and key == 'seg':
                output_dir = join(self.selected_folder, "Segmented_signals")
                makedirs(output_dir, exist_ok=True)
                output_path = join(output_dir, f"{base_name}_{suffix}.mat")
                savemat(output_path, {'epochs': data})
                self.log_message(f"Segmentation saved in: {output_path}")

            if self.paramsignalsCBox.isChecked() and key == 'param':
                output_dir = join(self.selected_folder, "Signal_parameters")
                makedirs(output_dir, exist_ok=True)
                self.log_message(f"Parameters: folder ready in {output_dir}")
                output_path = join(output_dir, f"{base_name}_{suffix}.mat")
                savemat(output_path, {'parameters': data})
                self.log_message(f"Parameters saved in: {output_path}")

        error_found = False
        for i, file in enumerate(selected_files):
            try:
                self.log_message(f"Processing file: {file}")
                self.progressLabel.setText(f"Processing: {basename(file)}")
                QtWidgets.QApplication.processEvents()

                base_name = splitext(basename(file))[0]
                data = medusa.components.Recording.load(file)
                current_signal = data.eeg.signal
                fs = data.eeg.fs

                band_seg = settings_dic['parameters'].get('band_segmentation', False)
                segmentation_type = settings_dic['segmentation']['segmentation_type']
                norm = settings_dic['segmentation']['norm'] or None
                bands = settings_dic['parameters'].get('selected_bands', []) if band_seg else [
                    {'name': 'broadband', 'min': settings_dic['parameters']['broadband_min'], 'max': settings_dic['parameters']['broadband_max']}]
                total_steps = total_files * len(bands)

                for j, band in enumerate(bands):
                    band_name = band.get('name', 'unknown')
                    bp_min, bp_max = band.get('min'), band.get('max')

                    # --------  Preprocessing -------
                    if settings_dic['preprocessing'].get('apply_preprocessing'):
                        cfg = {**settings_dic['preprocessing']}
                        if band_seg:
                            cfg.update({'bp_min': bp_min, 'bp_max': bp_max, 'bp_order': 1000})
                            signal_to_process = current_signal.copy()
                        else:
                            signal_to_process = current_signal

                        processed_signal = apply_preprocessing(signal_to_process, fs, cfg)
                        data.eeg.signal = processed_signal
                        save_outputs(deepcopy(data), base_name, band_name, 'prep')
                    else:
                        if band_seg:
                            processed_signal = band_segmentation(current_signal.copy(), bp_min, bp_max, fs)
                            data.eeg.signal = processed_signal
                        else:
                            processed_signal = current_signal

                    # --------  Segmentation and parameter's extraction -------
                    if segmentation_type == 'condition':
                        segment_by_condition(data, processed_signal, settings_dic, base_name, norm,
                                             band=band_name if band_seg else None)
                    elif segmentation_type == 'event':
                        segment_by_event(data, processed_signal, settings_dic, base_name, norm, fs,
                                         band=band_name if band_seg else None)

                    # Actualizar progreso
                    global_progress = int(((i * len(bands) + j + 1) / total_steps) * 100)
                    self.progressBar.setValue(global_progress)

            except Exception as e:
                error_found = True
                self.log_message(f"Error preprocessing {file}: {e}", style='error')
        return not error_found