import medusa
import json
import numpy as np
import os
from scipy.io import savemat

dir = r"D:\Proyectos\medusa-analyzer\prep_settings\settings.json"
with open(r"D:\Proyectos\medusa-analyzer\prep_settings\settings_prep_seg.json", "r") as f:
    settings_dic = json.load(f)

# def find_nearest_index(array, value):
#     array = np.array(array)
#     idx = (np.abs(array - value)).argmin()
#     return idx
#
# def find_nearest_index_array(reference_times, query_times):
#     reference_times = np.asarray(reference_times)
#     query_times = np.asarray(query_times)
#
#     indices = np.searchsorted(reference_times, query_times)
#     indices = np.clip(indices, 1, len(reference_times) - 1)
#
#     left = reference_times[indices - 1]
#     right = reference_times[indices]
#
#     closest = np.where(
#         np.abs(query_times - left) < np.abs(query_times - right),left,right)
#     return closest

def run_pipeline(settings_dic, total_tasks):
    import medusa
    import medusa.artifact_removal
    import numpy as np
    from os.path import basename, join, splitext
    from os import makedirs

    selected_files = settings_dic['preprocessing'].get('selected_files', [])
    total_files = len(selected_files)

    def apply_preprocessing(signal, fs, preprocessing_cfg):
        """Aplica filtros y CAR al EEG"""
        if preprocessing_cfg.get('bandpass'):
            bp_min = preprocessing_cfg.get('bp_min')
            bp_max = preprocessing_cfg.get('bp_max')
            bp_order = preprocessing_cfg.get('bp_order')
            if None not in (bp_min, bp_max, bp_order):
                bp_filter = medusa.FIRFilter(bp_order, [bp_min, bp_max], 'bandpass')
                signal = bp_filter.fit_transform(signal, fs)

        if preprocessing_cfg.get('notch'):
            notch_min = preprocessing_cfg.get('notch_min')
            notch_max = preprocessing_cfg.get('notch_max')
            notch_order = preprocessing_cfg.get('notch_order')
            if None not in (notch_min, notch_max, notch_order):
                notch_filter = medusa.FIRFilter(notch_order, [notch_min, notch_max], 'bandstop')
                signal = notch_filter.fit_transform(signal, fs)

        if preprocessing_cfg.get('car'):
            signal = medusa.car(signal)

        return signal

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

    def segment_by_condition(data, current_signal, settings, base_name, norm, band):
        from scipy import signal
        t_window = [0, int(settings['trial_length'])]
        trial_len = int(settings['trial_length'])*fs/1000
        norm_type = settings['norm_type'] if norm else None

        for cond in settings['selected_conditions']:
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
                    segment = current_signal[start:end, :]
                    epochs = medusa.get_epochs(segment, trial_len, norm=norm_type)
                    if epochs is not None:
                        segments.append(epochs)
                epoched = np.concatenate(segments, axis=0) if segments else None

                if settings["thresholding"]:
                    _, epoched, _ = medusa.artifact_removal.reject_noisy_epochs(epoched,
                                                                          np.nanmean(current_signal, axis=0),
                                                                          np.std(current_signal, axis=0),
                                                                          k=settings['thres_k'],
                                                                          n_samp=settings["thres_samples"],
                                                                          n_cha=settings["thres_channels"])
                if settings['resample']:
                    epoched = medusa.resample_epochs(epoched, t_window, settings['resample_fs'])
                    print(np.shape(epoched))

    def segment_by_event(data, current_signal, settings, base_name, norm, fs, band):
        w_start, w_end = settings['window_start'], settings['window_end']
        window = [w_start, w_end]
        if norm:
            norm_type = settings['norm_type']
            base_line_start, baseline_end = settings['baseline_start'], settings['baseline_end']
            baseline_window = [base_line_start, baseline_end]
        else:
            baseline_window = None
            norm_type = None

        for cond in settings['selected_conditions']:
            if cond == 'null':
                epoched = medusa.get_epochs(current_signal, int(settings['trial_length']), baseline_window, norm=norm_type)
            else:
                cond_key = data.marks.app_settings['conditions'][cond]['label']
                idx = get_condition_indices(data, cond_key)
                if len(idx) % 2 != 0:
                    continue

                for evt in settings['selected_events']:
                    evt_key = data.marks.app_settings['events'][evt]['label']
                    segments = []
                    for i in range(0, len(idx), 2):
                        start_idx = find_nearest_index(data.eeg.times, data.marks.conditions_times[idx[i]])
                        end_idx = find_nearest_index(data.eeg.times, data.marks.conditions_times[idx[i + 1]])
                        start_time = data.eeg.times[start_idx]
                        end_time = data.eeg.times[end_idx]

                        event_idx = get_event_indices_in_range(data, evt_key, start_time, end_time)
                        onsets = np.array(data.marks.events_times)[event_idx]
                        onsets_near = find_nearest_index_array(data.eeg.times, onsets)

                        epochs = medusa.get_epochs_of_events(data.eeg.times, current_signal, onsets_near, fs,
                                                             window, baseline_window, norm=norm_type)
                        if epochs is not None:
                            segments.append(epochs)

                    epoched = np.concatenate(segments, axis=0) if segments else None
                    if settings["thresholding"]:
                        epoched = medusa.artifact_removal.reject_noisy_epochs(epoched, np.nanmean(current_signal, axis=0), np.std(current_signal, axis=0),
                                                             k = settings['thres_k'],
                                                             n_samp = settings["thres_samples"],
                                                             n_cha = settings["thres_channels"])
                    if settings['resample']:
                        epoched = medusa.resample_epochs(epoched, window, settings['resample_fs'])


    for i, file in enumerate(settings_dic['preprocessing']['selected_files']):
        try:

            base_name = splitext(basename(file))[0]

            # ---------------------------------      BAND SEGMENTATION       --------------------------------
            if settings_dic['parameters'].get('band_segmentation'):
                selected_bands = settings_dic['parameters'].get('selected_bands', [])
                total_steps = total_files * max(1, len(selected_bands))

                for band in selected_bands:
                    data = medusa.components.Recording.load(file)
                    current_signal = data.eeg.signal
                    fs = data.eeg.fs

                    band_name = band.get('name', 'unknown')
                    bp_min, bp_max = band.get('min'), band.get('max')

                    # ---------------------- Preprocessing ------------------------ #
                    if settings_dic['preprocessing'].get('apply_preprocessing'):
                        preprocessing_cfg = settings_dic['preprocessing'].copy()
                        preprocessing_cfg.update({'bp_min': bp_min, 'bp_max': bp_max, 'bp_order': 1000})
                        current_band_signal = apply_preprocessing(current_signal.copy(), fs, preprocessing_cfg)
                        data.eeg.signal = current_band_signal
                    else:
                        data.eeg.signal = band_segmentation(current_signal.copy(), bp_min, bp_max, fs)

                    global_progress = int(((i + 1) / total_steps) * 100)

                    # ---------------------- Segmentation ------------------------ #
                    norm = settings_dic['segmentation']['norm'] or None
                    segmentation_type = settings_dic['segmentation']['segmentation_type']

                    if segmentation_type == 'condition':
                        segment_by_condition(data, current_signal, settings_dic['segmentation'], base_name, norm,
                                             band=band_name)

                    elif segmentation_type == 'event':
                        segment_by_event(data, current_signal, settings_dic['segmentation'], base_name, norm, fs,
                                         band=band_name)

            # ---------------------------------      BROADBAND       --------------------------------
            else:
                data = medusa.components.Recording.load(file)
                current_signal = data.eeg.signal
                fs = data.eeg.fs

                # ---------------------- Preprocessing ------------------------ #
                if settings_dic['preprocessing'].get('apply_preprocessing'):
                    current_signal = apply_preprocessing(current_signal, fs, settings_dic['preprocessing'])
                    data.eeg.signal = current_signal

                # ---------------------- Segmentation ------------------------ #
                norm = settings_dic['segmentation']['norm'] or None
                segmentation_type = settings_dic['segmentation']['segmentation_type']

                if segmentation_type == 'condition':
                    current_signal = segment_by_condition(data, current_signal, settings_dic['segmentation'], base_name, norm, band=None)

                elif segmentation_type == 'event':
                    current_singal = segment_by_event(data, current_signal, settings_dic['segmentation'], base_name, norm, fs, band=None)

                # -------------------- Parameters --------------------------- #

        except Exception as e:
            print(f"Error procesando {file}: {e}")

hola = run_pipeline(settings_dic,5)

# for file in settings_dic['preprocessing']['selected_files']:
#     print(file)
#
#     # Cargar el registro
#     data = medusa.components.Recording.load(file)
#     current_signal = data.eeg.signal # Trabajamos sobre esta
#
#     # --------- POR BANDAS -------------------
#     if settings_dic['parameters']['band_segmentation']:
#         print("Band segmentation habilitado. No se realiza procesamiento.")
#         selected_bands = settings_dic['parameters'].get('selected_bands', []) \
#             if settings_dic['parameters']['band_segmentation'] else [None]
#
#         for band in selected_bands:
#             band_name = band.get('name')
#             bp_min = band.get('min')
#             bp_max = band.get('max')
#
#         # ----------------- Preprocesado -------------
#             if settings_dic['preprocessing']['apply_preprocessing']:
#                 if settings_dic['preprocessing']['bandpass']:
#                     bp_filter = medusa.FIRFilter(1000, [bp_min, bp_max], 'bandpass')
#                     current_signal = bp_filter.fit_transform(current_signal, data.eeg.fs)
#
#                 if settings_dic['preprocessing']['notch']:
#                     notch_min = settings_dic['preprocessing']['notch_min']
#                     notch_max = settings_dic['preprocessing']['notch_max']
#                     notch_order = settings_dic['preprocessing']['notch_order']
#                     if None not in (notch_min, notch_max, notch_order):
#                         notch_filter = medusa.FIRFilter(notch_order, [notch_min, notch_max], 'bandstop')
#                         current_signal = notch_filter.fit_transform(current_signal, data.eeg.fs)
#
#                 if settings_dic['preprocessing']['car']:
#                     current_signal = medusa.car(current_signal)
#         # ---------------- Segmentation
#
#     # ---- SIN BANDAS
#     else:
#
#         # ----------------- Preprocesado -------------
#         if settings_dic['preprocessing']['apply_preprocessing']:
#             # --- Filtro Bandpass ---
#             if settings_dic['preprocessing']['bandpass']:
#                 print("Aplicando filtro bandpass...")
#
#                 bp_min = settings_dic['preprocessing']['bp_min']
#                 bp_max = settings_dic['preprocessing']['bp_max']
#                 bp_order = settings_dic['preprocessing']['bp_order']
#
#                 if None in (bp_min, bp_max, bp_order):
#                     print("Parámetros del filtro bandpass incompletos. Se omite este paso.")
#                 else:
#                     bandpass_bandwidth = [bp_min, bp_max]
#                     band_pass_filter = medusa.FIRFilter(bp_order, bandpass_bandwidth, 'bandpass')
#                     current_signal = band_pass_filter.fit_transform(current_signal, data.eeg.fs)
#                     print("Filtro bandpass aplicado correctamente.")
#             else:
#                 print("El filtro bandpass no está activado.")
#
#             # --- Filtro Notch ---
#             if settings_dic['preprocessing']['notch']:
#                 print("Aplicando filtro notch...")
#
#                 notch_min = settings_dic['preprocessing']['notch_min']
#                 notch_max = settings_dic['preprocessing']['notch_max']
#                 notch_order = settings_dic['preprocessing']['notch_order']
#
#                 if None in (notch_min, notch_max, notch_order):
#                     print("Parámetros del filtro notch incompletos. Se omite este paso.")
#                 else:
#                     notch_bandwidth = [notch_min, notch_max]
#                     notch_filter = medusa.FIRFilter(notch_order, notch_bandwidth, 'bandstop')
#                     current_signal = notch_filter.fit_transform(current_signal, data.eeg.fs)
#                     print("Filtro notch aplicado correctamente.")
#             else:
#                 print("El filtro notch no está activado.")
#
#             if settings_dic['preprocessing']['car']:
#                 print("Aplicando filtro car...")
#                 current_signal = medusa.car(current_signal)
#                 print("Filtro car aplicado correctamente.")
#             else:
#                 print("El filtro car no está activado.")
#
#         # ----------------- Segmentación -------------
#
#         if settings_dic['segmentation']['segmentation_type']=='condition':
#             selected_conditions = settings_dic['segmentation']['selected_conditions'] # ESTO ES UNA LISTA DE STRINGS
#             for selected_condition in selected_conditions: # iteramos por cada una de las condiciones seleccioandas
#                 if selected_condition == 'null':
#                     epoched_signal = medusa.get_epochs(current_signal, int(settings_dic['segmentation']['trial_length']))
#                 else:
#                     condition_key = data.marks.app_settings['conditions'][selected_condition]['label']
#                     idx = np.where(np.array(data.marks.conditions_labels) == condition_key)[0] # aqui quiero ver las posiciones en las que conditions key coincide con lo que hay en la lista de  data.marks.conditions_labels
#                     num = len(idx)
#                     if num % 2 == 0:
#                         trial_len = int(settings_dic['segmentation']['trial_length'])
#                         epoched_signals = None
#
#                         for i in range(0, num, 2):
#                             start = find_nearest_index(data.eeg.times, data.marks.conditions_times[idx[i]])
#                             end = find_nearest_index(data.eeg.times, data.marks.conditions_times[idx[i + 1]])
#                             selected = current_signal[start:end, :]
#                             epoched = medusa.get_epochs(selected, trial_len)
#                             if epoched_signals is None:
#                                 epoched_signals = epoched
#                             else:
#                                 epoched_signals = np.concatenate([epoched_signals, epoched], axis=0)
#
#
#         elif settings_dic['segmentation']['segmentation_type'] == 'event':
#
#             selected_conditions = settings_dic['segmentation']['selected_conditions']
#             selected_events = settings_dic['segmentation']['selected_events']
#             for selected_condition in selected_conditions:  # iteramos por cada una de las condiciones seleccioandas
#                 if selected_condition == 'null':
#                     epoched_signal = medusa.get_epochs(current_signal,int(settings_dic['segmentation']['trial_length']))
#                 else:
#                     condition_key = data.marks.app_settings['conditions'][selected_condition]['label']
#                     idx = np.where(np.array(data.marks.conditions_labels) == condition_key)[0]
#                     if len(np.where(np.array(data.marks.conditions_labels) == condition_key)[0]) % 2 == 0:
#                         epoched_signal = None
#                         for event in selected_events:
#                             event_key = data.marks.app_settings['events'][event]['label']
#                             for i in range(0, len(np.where(np.array(data.marks.conditions_labels) == condition_key)[0]),2):
#
#                                 start = find_nearest_index(data.eeg.times,data.marks.conditions_times[idx[i]])
#                                 end = find_nearest_index(data.eeg.times, data.marks.conditions_times[idx[i + 1]])
#                                 idx_events = np.where((np.array(data.marks.events_labels) == event_key) &
#                                                       (np.array(data.marks.events_times) >= data.eeg.times[start]) &
#                                                       (np.array(data.marks.events_times) <= data.eeg.times[end]))[0]
#
#                                 onsets = np.array(data.marks.events_times)[idx_events]
#                                 onsets_near = find_nearest_index_array(data.eeg.times, onsets)
#
#                                 epoched = medusa.get_epochs_of_events(data.eeg.times, current_signal, onsets_near, 250, [-50, 50])
#
#                                 if epoched_signal is None:
#                                     epoched_signal = epoched
#                                 else:
#                                     epoched_signal = np.concatenate([epoched_signal, epoched], axis=0)
#
#                 # output_path = join(dir, f"{base_name}_segmentation_{settings_dic['segementation']['segmentation_type']}_{suffix}.mat")
#                 # data.save_to_mat(output_path)
#         else:
#             print('segmentamos por eventos')
#
#
