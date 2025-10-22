from PySide6 import QtCore, QtGui, QtWidgets
import medusa
import medusa.artifact_removal
import medusa.transforms
from medusa.signal_metrics import central_tendency, median_frequency, shannon_spectral_entropy

import numpy as np
from os.path import basename, join, splitext
from pathlib import Path
import re
from os import makedirs
from copy import deepcopy
import neurokit2.ecg as nkecg
from neurokit2 import signal_rate, hrv
from neurokit2.signal import signal_psd

from scipy.stats import kurtosis, skew, zscore
from scipy.io import savemat

from eeg_features.experiments_to_semi_BIDS import output_path


def run_pipeline(controller, settings_dic):
    """
    Main pipeline function of the eeg features extraction that executes preprocessing, segmentation, and parameter
    computation for all selected files based on the provided configuration.
    """

    # Get the selected files and associated variables
    selected_files = settings_dic['files'].get('selected_files', [])
    total_files = len(selected_files)

    error_found = False

    view = controller.view

    # Config of the progress bar
    steps_per_lead = 2 + 4
    steps_per_file = 1 + steps_per_lead * len(settings_dic['leads']['selected_leads'])
    total_steps = total_files * steps_per_file # Total steps for the progress bar

    # Loop through each selected file
    for i, file in enumerate(selected_files):
        try:
            # Logging and GUI updates
            controller._log_message(f"Processing file: {file}")
            view.progressLabel.setText(f"Processing: {basename(file)}")
            QtWidgets.QApplication.processEvents()

            # Load data
            base_name = splitext(basename(file))[0]
            data = medusa.components.Recording.load(file)
            # Initialize variables
            name_signal = settings_dic['files']['selected_biosignal']  # ej: "eeg"
            original_signal = np.array(getattr(data, name_signal).signal)
            signal_times = getattr(data, name_signal).times
            channel_set = getattr(data, name_signal).channel_set
            signal_marks = include_no_conditions_in_marks(data.marks, signal_times)
            fs = getattr(data, name_signal).fs

            # Save original data
            save_outputs(controller, deepcopy(data), base_name, None, 'raw-signal', 'prep')
            # Ensure consistent sampling frequency
            if fs != settings_dic['preprocessing']['fs']:
                raise Exception("One of the selected signals do not have the same sampling frequency: " + file)

            # Update the progress bar and labels
            global_progress = (i*steps_per_file + 1) / total_steps * 100
            controller.view.progressBar.setValue(int(global_progress))

            ## First step: Select channels
            for j, chan_name in enumerate(settings_dic['leads']['selected_leads']):
                lead_name = settings_dic['leads']['selected_leads'][chan_name]
                idx_chan = channel_set['l_cha'].index(chan_name)

                original_signal_chan = deepcopy(original_signal[:, idx_chan])
                original_signal_chan = np.ravel(original_signal_chan)

                ## Second step: Preprocessing ECG
                processed_signal = deepcopy(original_signal_chan)
                if settings_dic['preprocessing']['clean'] or settings_dic['preprocessing']['zscore']:
                    processed_signal = clean_zscore_ecg(processed_signal, fs, settings_dic['preprocessing'])

                # Update the progress bar and labels
                global_progress = (i * steps_per_file + 1 + j * steps_per_lead + 1) / total_steps * 100
                controller.view.progressBar.setValue(int(global_progress))

                ## Third step: Separate by condition
                segments = []
                conditions = []
                if settings_dic['leads']['selected_conditions']:
                    for cond in settings_dic['segmentation']['selected_conditions']:
                        segments.append(get_epochs_from_condition(processed_signal, cond, signal_marks, signal_times, fs))
                        conditions.append(cond)
                else:
                    segments.append(deepcopy(processed_signal))
                    conditions.append('all')

                # Update the progress bar and labels
                global_progress = (i * steps_per_file + 1 + j * steps_per_lead + 2) / total_steps * 100
                controller.view.progressBar.setValue(int(global_progress))

                # For each segment (condition)...
                for segment_idx, segment in enumerate(segments):

                    cond = conditions[segment_idx]
                    save_outputs(controller, deepcopy(segment), base_name, lead_name, cond, 'prep')
                    ## Fourth step: HRV computation
                    if settings_dic['preprocessing']['hrv']:
                        method = settings_dic['preprocessing']['processing_method']
                        correction = settings_dic['preprocessing']['correct_artifacts']
                        peaks, _ = nkecg.ecg_peaks(segment, sampling_rate=fs, method=method, correct_artifacts=correction)
                        pulse_rate = signal_rate(peaks, sampling_rate=fs)
                        hrv_signal = np.divide(60, pulse_rate) * 1000 # In ms

                        ## Fifth step: Resample HRV
                        fs_hrv = settings_dic['preprocessing']['resample_fs']
                        t_hrv = np.cumsum(hrv_signal)
                        t_uniform = np.arange(0, t_hrv[-1], 1/fs_hrv)
                        hrv_signal = np.interp(t_uniform, t_hrv, hrv_signal)
                        hrv_basename = str(Path(base_name).with_name(Path(base_name).stem + '_hrv' + Path(base_name).suffix))
                        save_outputs(controller, deepcopy(hrv_signal), hrv_basename, lead_name, cond, 'prep')

                        ## Fifth step: Save outputs
                        params = compute_parameters_hrv(peaks, hrv_signal, fs, fs_hrv, settings_dic['parameters'])
                        save_outputs(controller, deepcopy(params), hrv_basename, lead_name, cond, 'param')

                # Update the progress bar and labels
                global_progress = (i * steps_per_file + 1 + j * steps_per_lead + 6) / total_steps * 100
                controller.view.progressBar.setValue(int(global_progress))

            view.progressLabel.setText("Completed")
        # Exception handling
        except Exception as e:
            error_found = True
            controller._log_message(f"Error preprocessing {file}: {e}", style='error')
            view.progressLabel.setText("Error")

    return error_found

#################### HELPER FUNCTIONS

def include_no_conditions_in_marks(marks, times):
    # Create a copy of marks
    new_marks = deepcopy(marks)

    # The label for no-condition will be the max label + 1
    if marks.conditions_labels:
        new_label = np.max(marks.conditions_labels) + 1
    else:
        new_label = 0
    # Include the no-condition condition in the app_settings
    new_marks.app_settings['conditions']['no-condition'] = {'desc-name': 'No Condition',
                                                             'label': new_label,
                                                             'shortcut': 'NA'}

    # Get the conditions times and labels from the original marks
    conditions_times = np.array(marks.conditions_times).reshape(-1, 2)
    conditions_labels = np.array(marks.conditions_labels).reshape(-1, 2)[:,0]

    # Convert the times to indices of the 'times' array
    ranges = []
    # For each condition
    for (start_t, end_t), label in zip(conditions_times, conditions_labels):
        # Get the closest indices in 'times' for the initial and final timestamps
        start_idx = np.searchsorted(times, start_t)
        end_idx = np.searchsorted(times, end_t)
        # Append them in the ranges variable
        ranges.append((start_idx, end_idx, label))

    if ranges:
        # Add intervals where there is no label with "new_label" (i.e., fill the no-condition gaps)
        final_ranges = []
        prev_end = 0
        # For each range in ranges
        for start, end, label in ranges:
            # Check if there is a gap between the previous end and the current start
            if prev_end < start:
                # If so, append a new range with label "new_label"
                final_ranges.append((prev_end, start, new_label))
            # Append the current range (the range of the already existing condition)
            final_ranges.append((start, end, label))
            # The current end becomes the previous end for the next iteration
            prev_end = end
    else:
        # If there are no ranges (no conditions), the entire signal is no-condition
        final_ranges = [(0, len(times), new_label)]
        prev_end = len(times)

    # If there is a gap between the last end and the end of the signal, also append it as a "new_label" (i.e.,
    # no-condition) range
    if prev_end < len(times):
        final_ranges.append((prev_end, len(times), new_label))

    # Create the new conditions_times and conditions_labels arrays
    new_conditions_times = []
    new_conditions_labels = []
    # For each range in final_ranges
    for start_idx, end_idx, label in final_ranges:
        # Append the start and end times. The end_idx is actually the beginning of the next range, so we use end_idx - 1
        # to get the actual end time of the current range
        new_conditions_times.append([times[start_idx], times[end_idx - 1]])
        # Append the label twice (start and end)
        new_conditions_labels.append(label)
        new_conditions_labels.append(label)
    # Convert to numpy arrays
    new_conditions_times = np.array(new_conditions_times).flatten() # Flatten the array
    new_conditions_labels = np.array(new_conditions_labels)

    # Include the new conditions times and labels in the new marks
    new_marks.conditions_times = new_conditions_times
    new_marks.conditions_labels = new_conditions_labels

    return new_marks


def get_epochs_from_condition(signal, condition, marks, times, fs):
    """
    Extract epochs from the signal based on specified condition names
    """
    # Get the label (numerical value) associated with the condition name
    cond_key = marks.app_settings['conditions'][condition]['label']

    # Find indices of epochs matching the condition label
    idx = np.where(np.array(marks.conditions_labels) == cond_key)[0]
    # Skip if odd number of indices (requires pairs of start/end)
    if len(idx) % 2 != 0:
        return False

    # Segment into epochs
    segments = []
    # For each pair of start/end indices
    for i in range(0, len(idx), 2):
        # Start and end sample indices of the conditions
        start = _find_nearest_index(times, marks.conditions_times[idx[i]])
        end = _find_nearest_index(times, marks.conditions_times[idx[i + 1]])
        # Extract segment
        segment = signal[start:end]
        # Get epochs from the segment
        epochs = medusa.get_epochs(segment, segment.shape[0])

        # Append if epochs were created
        if epochs is not None:
            segments.append(epochs)

    return segments
def _find_nearest_index(reference_times, query_times):
    """
    Find the index (or indices) in reference_times closest to query_times.
    """
    # References times is the times vector
    reference_times = np.asarray(reference_times)
    # Query times is the markers of the conditions
    query_times = np.atleast_1d(query_times)  # Ensure we always work with an array (i.e., convert scalars to 1D array)

    # Find indices where query_times would be inserted into reference_times to keep order
    indices = np.searchsorted(reference_times, query_times)

    # In the next step we will index using "indices" and "indices - 1". This means that we now have to avoid indices
    # being 0 or len(reference_times), as this would lead to out-of-bounds indexing in the next step. We will clip the
    # indices so that all of their values are between 1 and len(reference_times) - 1, ensuring that both "indices" and
    # "indices - 1" are within valid range (i.e., not 0 and not len(reference_times))
    indices = np.clip(indices, 1, len(reference_times) - 1)

    # Get the left and right neighbors of each query time
    left = reference_times[indices - 1]
    right = reference_times[indices]

    # Choose the closest neighbor (right or left)
    choose_left = np.abs(query_times - left) < np.abs(query_times - right) # Choose left if it's closer than right
    # nearest_indices will contain indices - 1 if left is closer, or indices if right is closer
    nearest_indices = np.where(choose_left, indices - 1, indices)

    # If the input was a single value, return a single index. This if covers two ways of providing a single value: as a
    # scalar and as a one-element array
    if np.isscalar(query_times) or query_times.shape == (1,):
        return nearest_indices[0]

    # If the input was an array, return an array of indices
    return nearest_indices

def save_outputs(controller, data, base_name, lead, cond, key):
    """
    Guarda los resultados del pipeline en estructura semi-BIDS dentro de /derivatives.

    Estructura:
    derivatives/
        ├── preprocessed/
        └── parameters/
    """
    selected_folder = Path(controller.view.selected_folder)
    derivatives_path = selected_folder / "derivatives"
    derivatives_path.mkdir(exist_ok=True)

    # Obtener info del sujeto y sesión desde el nombre del archivo base
    subj_match = re.search(r"(sub-\d+)", base_name)
    ses_match = re.search(r"(ses-\d+)", base_name)
    subj_id = subj_match.group(1) if subj_match else "sub-" + base_name.split('.')[0]
    ses_id = ses_match.group(1) if ses_match else None
    base_stem = Path(base_name).stem
    # --- Saving preprocessed signals (.rec.bson) ---
    if key == "prep" and controller.view.prepsignalsCBox.isChecked():
        if ses_id:
            preproc_dir = derivatives_path / "preprocessed" / subj_id / ses_id / "ecg"
        else:
            preproc_dir = derivatives_path / "preprocessed" / subj_id / "ecg"
        preproc_dir.mkdir(parents=True, exist_ok=True)

        if lead is not None:
            output_path = preproc_dir / f"{base_stem}_lead-{lead.replace("-", "")}_cond-{cond.replace("-", "")}.rec.bson"
        else:
            output_path = preproc_dir / f"{base_stem}_cond-{cond.replace("-", "")}.rec.bson"
        if hasattr(data, "save"):
            data.save(str(output_path))
        elif hasattr(data, "save_to_bson"):
            data.save_to_bson(str(output_path))
        else:
            try:
                savemat(output_path, {'data': data})
            except Exception:
                raise RuntimeError('Error saving')

        controller._log_message(f"✅ Preprocessed saved: {output_path}")

    # --- Saving parameters (.mat) ---
    if key == "param" and controller.view.paramsignalsCBox.isChecked():
        if ses_id:
            param_dir = derivatives_path / "parameters" / subj_id / ses_id / "ecg"
        else:
            param_dir = derivatives_path / "parameters" / subj_id / "ecg"
        param_dir.mkdir(parents=True, exist_ok=True)

        if not isinstance(data, dict):
            outname = f"{subj_id}_param-unknown_lead-{lead.replace("-", "")}_cond-{cond.replace("-", "")}.mat"
            outpath = param_dir / outname
            savemat(outpath, {'parameters': data})
            controller._log_message(f"⚠️ Parameters: saved fallback file {outpath}")
            return

        params_dict = dict(data)

        # 1) PSDs: (psd_<band> + psd_freqs_<band>)
        psd_bands = set()
        for k in list(params_dict.keys()):
            if k.startswith('psd_'):
                psd_bands.add(k[4:])
            if k.startswith('psdfreqs_'):
                psd_bands.add(k[10:])

        for b in psd_bands:
            psd_key = f'psd{b}'
            freqs_key = f'psdfreqs{b}'
            psd_val = params_dict.pop(psd_key, None)
            freqs_val = params_dict.pop(freqs_key, None)

            metric_label = (f"psd{b}")
            outname = f"{base_stem}_param-{metric_label.replace("-", "")}_lead-{lead.replace("-", "")}_cond-{cond.replace("-", "")}.mat"
            outpath = param_dir / outname

            save_struct = {}
            if psd_val is not None:
                save_struct['psd'] = np.asarray(psd_val)
            if freqs_val is not None:
                save_struct['freqs'] = np.asarray(freqs_val)

            mat_dict = {metric_label: save_struct}

            savemat(outpath, mat_dict)
            controller._log_message(f"✅ Parameter saved: {outpath}")

        # 2) Other parameters
        for k, v in list(params_dict.items()):
            metric_label = k.replace('_', '-')

            outname = f"{base_stem}_param-{metric_label.replace("-", "")}_lead-{lead.replace("-", "")}_cond-{cond.replace("-", "")}.mat"
            outpath = param_dir / outname

            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict) and 'band' in v[0]:
                rp_struct = {}
                for entry in v:
                    bname = entry.get('band', 'unknown')
                    rp_struct[bname] = np.asarray(entry.get('value'))
                savemat(outpath, {metric_label: rp_struct})

            elif isinstance(v, dict):
                nested = {}
                for kk, vv in v.items():
                    nested[kk] = np.asarray(vv)
                savemat(outpath, {metric_label: nested})
            else:
                try:
                    savemat(outpath, {metric_label: np.asarray(v)})
                except Exception:
                    savemat(outpath, {'value': np.asarray(v)})

            controller._log_message(f"✅ Parameter saved: {outpath}")

#################### PREPROCESSING

def clean_zscore_ecg(signal, fs, cfg):
    """
    Apply bandpass, notch filtering, and Common Average Reference (CAR).
    """

    # Baseline correction
    if cfg['clean']:
        signal = nkecg.ecg_clean(signal, sampling_rate=fs, method=cfg['clean_method'])

    # Zscore and return
    return zscore(signal, axis=0) if cfg['zscore'] else signal


##################### BAND FILTERING

def band_filtering(signal, bp_min, bp_max, fs, cfg):
    """
    Apply band segmentation with a FIR bandpass filter. Used when preprocessing is disabled but band-specific
    segmentation is required.
    """
    order = 1000 if cfg['bandpass'] is False else cfg['bp_order']
    win = 'hamming' if cfg['bandpass'] is False else cfg['bp_win']
    bp_filter = medusa.FIRFilter(order, [bp_min, bp_max], 'bandpass', window=win)
    signal = bp_filter.fit_transform(signal, fs)
    return signal

##################### BAND FILTERING

def compute_parameters_hrv(peaks, hrv_signal, fs, fs_hrv, cfg):

    # Initialize dict that will contain all the computed parameters
    params = {}

    # Get the parameters provided by neurokit2
    params_nk = hrv(peaks, sampling_rate=fs)

    # TIME METRICS
    time_funcs = {
        'pulse_rate': '',
        'averege': 'MeanNN',
        'std_nn': 'SDNN',
        'rms_sucessive_diff': 'RMSSD',
        'std_sucessive_diff': 'SDSD',
        'variation_coef': 'CVNN',
        'tring_interp': 'TINN',
        'pnn20': 'pNN20',
        'pnn50': 'pNN50'}

    # For each parameter...
    for name, name_nk in time_funcs.items():
        try:
            # If selected...
            if cfg[name]:
                # Store in the params dict
                if name == 'pulse_rate':
                    params[f"{name}"] = signal_rate(peaks, sampling_rate=fs)
                else:
                    params[f"{name}"] = params_nk['HRV_' + name_nk][0]
        except Exception:
            params[f"{name}"] = np.nan


    # SPECTRAL METRICS

    # Compute PSD
    try:
        psd = signal_psd(peaks['ECG_R_Peaks'].to_numpy(), sampling_rate=fs_hrv, max_frequency=0.55, window_type="hann", order=16)
    except Exception:
        psd = None

    spectral_funcs = {
        'psd': psd,
        'sympathovagal_balance': params_nk['HRV_LFHF'][0],
    }
    # For each parameter...
    for name, name_nk in spectral_funcs.items():
        # If selected...
        if cfg[name]:
            try:
                # Store in the params dict
                params[f"{name}"] = name_nk
            except Exception:
                params[f"{name}"] = np.nan

    spectral_funcs_bands = {
        'power': '',
        'median_frequency': lambda band: medusa.signal_metrics.median_frequency.median_frequency(psd['Power'].to_numpy()[np.newaxis, ..., np.newaxis], fs_hrv, [band['min'], band['max']]),
        'spectral_entropy': lambda band: medusa.signal_metrics.shannon_spectral_entropy.shannon_spectral_entropy(psd['Power'].to_numpy()[np.newaxis, ..., np.newaxis], fs_hrv, [band['min'], band['max']]),
        'kurtosis': lambda _: float(kurtosis(peaks, axis=0)),
        'skewness': lambda _: float(skew(peaks, axis=0)),
    }
    if cfg['selected_bands'] is not None:
        for band in cfg['selected_bands']:
            band_name = 'TP' if band['name'] == 'Broadband' else band['name']
            # For each parameter...
            for name, func in spectral_funcs_bands.items():
                # If selected...
                if cfg[name]:
                    try:
                        if name == 'power':
                            params[f"{name}_{band_name}"] = params_nk[f'HRV_{band_name}'][0]
                        else:
                            # Store in the params dict
                            params[f"{name}_{band_name}"] = func(band)
                    except Exception:
                        params[f"{name}_{band_name}"] = np.nan

    # NONLINEAR METRICS
    nonlinear_funcs = {
        'ctm': lambda: np.ravel(medusa.signal_metrics.central_tendency.central_tendency_measure(np.expand_dims(hrv_signal, axis=(0, 2)),cfg['ctm_r'])),
        'sample_entropy': ['SampEn'],
        'shannon_entropy': ['ShanEn'],
        'lzc': ['LZC'],
        "dfa": ['DFA_alpha1', 'DFA_alpha2'],
        "poincare": ['SD1', 'SD2', 'SD1SD2', 'S']
    }

    # For each parameter...
    for name, name_nk_func in nonlinear_funcs.items():
        # If selected...
        if cfg[name]:
            try:
                if name == 'ctm':
                    params[f"{name}"] = name_nk_func()
                elif len(name_nk_func) > 1:
                    for subname in name_nk_func:
                        params[f"{subname}"] = params_nk['HRV_' + subname][0]
                else:
                    # Store in the params dict
                    params[f"{name}"] = params_nk['HRV_' + name_nk_func[0]][0]
            except Exception:
                if name == 'ctm':
                    params[name] = np.nan
                elif len(name_nk_func) > 1:
                    for subname in name_nk_func:
                        params[subname] = np.nan
                else:
                    params[name] = np.nan

    return params

def load_config(files_widget, data):
    """
    Loads configuration from a saved JSON-like dict for the ECG processing module.
    """

    # BIOSIGNAL INFO
    biosignal_txt = files_widget.biosignalBox.currentText()
    biosignal = biosignal_txt.split(" ")[1]
    files_widget.controller.biosignal_info = files_widget.controller.biosignals[biosignal]

    # --- LEADS ---
    # lead_cfg = data["leads"]
    # leads_widget = files_widget.main_window.stackedWidget.widget(2)
    # # Set selected leads
    # selected_leads = lead_cfg.get("selected_leads", {})
    # if hasattr(leads_widget, "controller"):
    #     leads_widget.controller.selected_leads = selected_leads
    #     leads_widget.controller.selected_conditions = lead_cfg.get("selected_conditions", [])
    #
    # layout = leads_widget.LeadsSelection.layout()
    # if layout is None:
    #     return
    # for i in range(layout.count()):
    #     row_widget = layout.itemAt(i).widget()
    #     if not row_widget:
    #         continue
    #
    #     checkbox = row_widget.findChild(QtWidgets.QCheckBox)
    #     combo = row_widget.findChild(QtWidgets.QComboBox)
    #
    #     if not checkbox or not combo:
    #         continue
    #
    #     channel_name = checkbox.text().replace("Channel ", "").strip()
    #     if channel_name in selected_leads:
    #         checkbox.setChecked(True)
    #         desired_lead = selected_leads[channel_name]
    #         index = combo.findText(desired_lead)
    #         if index != -1:
    #             combo.setCurrentIndex(index)
    #     else:
    #         checkbox.setChecked(False)
    #
    # if len(selected_leads) == 1:
    #     leads_widget.leadLabel.setText(list(selected_leads.values())[0])
    # elif len(selected_leads) > 1:
    #     leads_widget.leadLabel.setText(", ".join(selected_leads.values()))
    # else:
    #     leads_widget.leadLabel.clear()

    # --- PREPROCESSING ---
    prep_cfg = data["preprocessing"]
    preproc_widget = files_widget.main_window.stackedWidget.widget(3)  # widget(3): preprocessing
    preproc_widget.cleanCBox.setChecked(bool(prep_cfg["clean"]))
    preproc_widget.zscoreCBox.setChecked(bool(prep_cfg["zscore"]))
    preproc_widget.hrvCBox.setChecked(bool(prep_cfg["hrv"]))
    preproc_widget.cleanBox.setCurrentText(prep_cfg["processing_method"])
    preproc_widget.artifactsCBox.setChecked(bool(prep_cfg["correct_artifacts"]))
    if "resample_fs" in prep_cfg:
        preproc_widget.resampleBox.setValue(prep_cfg["resample_fs"])
    files_widget.main_window.controller.preproc_config = prep_cfg

    # --- PARAMETERS ---
    params_cfg = data["parameters"]
    params_widget = files_widget.main_window.stackedWidget.widget(4)  # widget(4): parameters

    # Set general analysis options
    params_widget.pulserateCBox.setChecked(bool(params_cfg["pulse_rate"]))
    params_widget.avnnCBox.setChecked(bool(params_cfg["average"]))
    params_widget.sdnnCBox.setChecked(bool(params_cfg["std_nn"]))
    params_widget.rmssdCBox.setChecked(bool(params_cfg["rms_sucessive_diff"]))
    params_widget.sdsdCBox.setChecked(bool(params_cfg["std_sucessive_diff"]))
    params_widget.vcCBox.setChecked(bool(params_cfg["variation_coef"]))
    params_widget.tinnCBox.setChecked(bool(params_cfg["tring_interp"]))
    params_widget.pnn20CBox.setChecked(bool(params_cfg["pnn20"]))
    params_widget.pnn50CBox.setChecked(bool(params_cfg["pnn50"]))
    params_widget.psdCBox.setChecked(bool(params_cfg["psd"]))
    params_widget.svbCBox.setChecked(bool(params_cfg["sympathovagal_balance"]))
    params_widget.controller.update_band_label(params_cfg["selected_bands"])
    params_widget.powerCBox.setChecked(bool(params_cfg["power"]))
    params_widget.kurtCBox.setChecked(bool(params_cfg["kurtosis"]))
    params_widget.skewnessCBox.setChecked(bool(params_cfg["skewness"]))
    params_widget.mfCBox.setChecked(bool(params_cfg["median_frequency"]))
    params_widget.seCBox.setChecked(bool(params_cfg["spectral_entropy"]))
    params_widget.ctmCBox.setChecked(params_cfg['ctm'] if params_cfg['ctm'] is not None else False)
    params_widget.ctmrBox.setValue(
        params_cfg['ctm_r'] if params_cfg['ctm_r'] is not None else params_widget.defaults['ctmradius'])
    params_widget.sampenCBox.setChecked(
        params_cfg['sample_entropy'] if params_cfg['sample_entropy'] is not None else False)
    params_widget.sampenrBox.setValue(
        params_cfg['sample_entropy_r'] if params_cfg['sample_entropy_r'] is not None else params_widget.defaults[
            'sampradius'])
    params_widget.sampenmBox.setValue(
        params_cfg['sample_entropy_m'] if params_cfg['sample_entropy_m'] is not None else params_widget.defaults[
            'sampm'])
    params_widget.shaeCBox.setChecked(bool(params_cfg["shannon_entropy"]))
    params_widget.lzcCBox.setChecked(bool(params_cfg["lzc"]))
    params_widget.dfaCBox.setChecked(
        params_cfg['dfa'] if params_cfg['dfa'] is not None else False)
    params_widget.dfanBox.setValue(
        params_cfg['dfa_n'] if params_cfg['dfa_n'] is not None else params_widget.defaults[
            'dfan'])
    params_widget.dfabBox.setValue(
        params_cfg['dfa_b'] if params_cfg['dfa_b'] is not None else params_widget.defaults[
            'dfab'])
    params_widget.poincareCBox.setChecked(bool(params_cfg["poincare"]))

    files_widget.main_window.controller.parameters_config = params_cfg