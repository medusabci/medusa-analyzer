import os
from PySide6 import QtWidgets
import scipy.io as sio
from medusa.meeg.meeg import *
from medusa.components import Recording, CustomExperimentData
import re
import shutil
from pathlib import Path

from medusa.bci import erp_spellers
from medusa import ecg
# README: To include a new converter, just create a function that takes a file path as input (e.g.
# _convert_newformat_file(filepath)) and returns the new filepath, and include it in the CONVERTERS dictionary with the
# corresponding file extension.

# TODO : ECG NO FUNCIONA, QUE DEJE CARGAR CARPETAS, MAS CLARA INTERACCION CON PATHS


def convert_to_semi_bids(input_path, output_path, anat):
    '''
    output_path/
    │
    output_path/
        │
        ├── sub-01/
        │   └── ses-01/
        │       └── eeg/
        │           ├── sub-01_run-01.rec.bson
        │           ├── sub-01_run-02.rec.bson
        │           └── ...
        │
        ├── sub-02/
        │   └── eeg/
        │       ├── sub-02_run-01.rec.bson
        │       └── ...
        │
        └── ......
        '''

    all_final_files = []
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    subject_pattern = re.compile(r'(?:sujeto[_\s-]*|sub[_\s-]*|s)(\d+)', re.IGNORECASE)
    session_pattern = re.compile(r'(?:sesion[_\s-]*|session[_\s-]*|ses[_\s-]*)(\d+)', re.IGNORECASE)
    record_pattern = re.compile(
        r'(?:run[_\s-]*|r[_\s-]*|recording[_\s-]*|rec[_\s-]*|registro[_\s-]*|ran[_\s-]*)(\d+)',
        re.IGNORECASE
    )

    subj_dirs = [d for d in input_path.iterdir() if d.is_dir()]
    if not subj_dirs:  # if not folders, we consider the input path as a unique subject
        subj_dirs = [input_path]

    for subj_dir in subj_dirs:
        subj_match = subject_pattern.search(subj_dir.name)
        subj_id = subj_match.group(1).zfill(2) if subj_match else "01"

        subj_bids_path = output_path / f"sub-{subj_id}"
        subj_bids_path.mkdir(exist_ok=True)

        # Detect sessions
        session_dirs = [d for d in subj_dir.iterdir() if d.is_dir() and session_pattern.search(d.name)]
        if session_dirs:
            for ses_dir in session_dirs:
                ses_match = session_pattern.search(ses_dir.name)
                ses_id = ses_match.group(1).zfill(2)
                ses_bids_path = subj_bids_path / f"ses-{ses_id}"
                ses_bids_path.mkdir(exist_ok=True)
                files_from_process = process_recordings(ses_dir, ses_bids_path, anat, record_pattern)
                all_final_files.extend(files_from_process)
        else:
            files_from_process = process_recordings(subj_dir, subj_bids_path, anat, record_pattern)
            all_final_files.extend(files_from_process)

    print("✅ Conversion to semi-BIDS completed.")

    return all_final_files

def process_recordings(source_dir, dest_root, anat, record_pattern):
    anat_dir = dest_root / anat
    anat_dir.mkdir(parents=True, exist_ok=True)

    rec_files = [f for f in source_dir.iterdir() if f.is_file() and ''.join(f.suffixes).lower().endswith(".rec.bson")]
    if not rec_files:
        return []

    subj_match = re.search(r'sub-(\d+)', str(dest_root))
    subj_id = subj_match.group(1) if subj_match else "01"

    final_files = []

    for file in sorted(rec_files):
        rec_match = record_pattern.search(file.name)
        run_id = rec_match.group(1).zfill(2) if rec_match else "01"

        new_name = f"sub-{subj_id}_run-{run_id}.rec.bson"
        dest_file = anat_dir / new_name
        shutil.copy2(file, dest_file)
        final_files.append(dest_file)
        print(f"📄 Copied: {file.name} → {dest_file.relative_to(dest_root)}")

    return final_files

from pathlib import Path
import numpy as np
import scipy.io as sio
from medusa.components import Recording, CustomExperimentData
from medusa.meeg.meeg import EEG, EEGChannelSet


def _convert_rcp_file(file, log_browser=None, output_dir=None):
    """
    Convert RCP file to REC format.
    - Does NOT modify the original file.
    - Always saves the new .rec.bson file inside output_dir.
    - If a file with the same name already exists in output_dir, appends a numeric suffix.
    """
    file = Path(file)
    if output_dir is None:
        raise ValueError("Output directory must be provided for safe conversion (no overwriting).")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create unique output filename inside output_dir
    base_name = file.stem.replace(".rcp", "")  # clean possible double extension
    new_file = output_dir / f"{base_name}.rec.bson"
    counter = 1
    while new_file.exists():
        new_file = output_dir / f"{base_name}_{counter}.rec.bson"
        counter += 1

    try:
        # Create Recording object
        subj_id = file.stem.split('.')[0]
        recording = Recording(subject_id=subj_id)

        # Load original data
        data = Recording.load(str(file))

        # Extract ERP marks
        marks = CustomExperimentData()
        marks.events_labels = (
            data.erpspellerdata.erp_labels.tolist()
            if isinstance(data.erpspellerdata.erp_labels, np.ndarray)
            else data.erpspellerdata.erp_labels
        )
        marks.events_times = (
            data.erpspellerdata.onsets.tolist()
            if isinstance(data.erpspellerdata.onsets, np.ndarray)
            else data.erpspellerdata.onsets
        )
        marks.app_settings = {
            'events': {'target': {'label': 0}, 'non_target': {'label': 1}},
            'conditions': {'no-condition': {'label': 0}},
        }
        marks.conditions_labels = []
        marks.conditions_times = np.empty((0, 2))

        # Fill the Recording object
        recording.add_biosignal(biosignal=data.eeg)
        recording.add_experiment_data(marks, key='marks')

        # Save converted file ONLY inside output_dir
        recording.save(str(new_file))
        return str(new_file)

    except Exception as e:
        if log_browser:
            log_browser.append(f"❌ Error converting RCP file: {e}")
        return None


def _convert_mat_file(file, log_browser=None, output_dir=None):
    """
    Convert MAT file to REC format.
    - Does NOT modify the original .mat file.
    - Always saves the new .rec.bson inside output_dir.
    - If a file with the same name already exists in output_dir, appends a numeric suffix.
    """
    file = Path(file)
    if output_dir is None:
        raise ValueError("Output directory must be provided for safe conversion (no overwriting).")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create unique output filename inside output_dir
    base_name = file.stem.replace(".mat", "")
    new_file = output_dir / f"{base_name}.rec.bson"
    counter = 1
    while new_file.exists():
        new_file = output_dir / f"{base_name}_{counter}.rec.bson"
        counter += 1

    try:
        subj_id = file.stem.split('.')[0]
        recording = Recording(subject_id=subj_id)

        # Load MATLAB data
        mat = sio.loadmat(file, struct_as_record=False, squeeze_me=True)
        data = mat["data"]

        # Create empty marks
        marks = _create_empty_marks()

        # Build channel set depending on file type
        if "SOURCES" in file.name.upper():
            ROIs = [{"label": f"ROI_{i+1}", "coord": "all", "reference": None}
                    for i in range(data.signal.shape[1])]
            channel_set = EEGChannelSet(reference_method="average")
            channel_set.set_montage(channels=ROIs, allow_unlocated_channels=True)

        elif "MEG" in file.name.upper():
            channels = [{"label": f"MEG_{i+1}", "coord": "all", "reference": None}
                        for i in range(data.signal.shape[1])]
            channel_set = EEGChannelSet(reference_method="average")
            channel_set.set_montage(channels=channels, allow_unlocated_channels=True)

        else:  # Default EEG case
            channels = data.cfg.channels
            replacements = {'T3': 'T7', 'T4': 'T8', 'T5': 'P7', 'T6': 'P8'}
            replace_func = np.vectorize(lambda x: replacements.get(x, x))
            channels = replace_func(channels)
            channel_set = EEGChannelSet()
            channel_set.set_standard_montage(l_cha=channels, montage='10-05')

        # Create EEG object
        times = np.linspace(0, data.signal.shape[0] / data.cfg.fs, data.signal.shape[0], endpoint=False)
        eeg = EEG(times=times, signal=data.signal, fs=data.cfg.fs, channel_set=channel_set)

        # Fill and save recording
        recording.add_biosignal(biosignal=eeg)
        recording.add_experiment_data(marks, key='marks')

        recording.save(str(new_file))
        return str(new_file)

    except Exception as e:
        if log_browser:
            log_browser.append(f"❌ Error converting MAT file: {e}")
        return None


def _convert_rec_file(file):
    """
    Normalize REC file: ensure it always contains an 'marks' entry.
    """
    # Load the recording
    data = Recording.load(file)

    # Check if 'marks' attribute exists
    if not hasattr(data, "marks") or data.marks is None:
        marks = _create_empty_marks()
        data.add_experiment_data(marks, key="marks")

    # Return the normalized file path
    return file


# Converter registry
CONVERTERS = {
    ".rcp.bson": {
        "converter": _convert_rcp_file
    },
    ".mat": {
        "converter": _convert_mat_file
    },
    ".rec.bson": {
        "converter": _convert_rec_file
    }
}


def _log_message(log_browser, message):
    """Helper function for logging messages"""
    if log_browser:
        log_browser.append(message)
        QtWidgets.QApplication.processEvents()


def _update_progress(progress_bar, current, total):
    """Helper function for updating progress bar"""
    if progress_bar:
        progress_bar.setValue(int((current + 1) / total * 100))
        QtWidgets.QApplication.processEvents()


def _create_empty_marks():
    """Create empty marks structure"""
    marks = CustomExperimentData()
    marks.events_labels = []
    marks.events_times = []
    marks.conditions_labels = []
    marks.conditions_times = np.empty((0, 2))
    marks.app_settings = {'conditions': {}, 'events': {}}
    return marks


def _run_converter(converter, file, log_browser=None, output_dir=None):
    """
    Try to run converter(file, log_browser). If the converter doesn't accept
    the extra arg, fallback to converter(file).
    Return the converter result (path) or None if it fails.
    """
    data = None
    try:
        result = converter(file, log_browser, output_dir=output_dir)
    except TypeError:
        try:
            result = converter(file, log_browser)
        except TypeError:
            result = converter(file)

    if result and os.path.exists(result):
        if output_dir:
            dest = Path(output_dir) / Path(result).name
            if str(Path(result).resolve()) != str(dest.resolve()):
                shutil.copy2(result, dest)
            return str(dest)
        return str(result)

    return None


def conversor_to_rec(files, progress_bar=None, log_browser=None, main_window=None):
    """
    Convert different file types to .rec.bson format and arrange them in semi-BIDS structure.
    - If a file is .rec.bson and already contains data.marks -> skip.
    - If a file is .rec.bson and lacks data.marks -> run the normalizer converter.
    - For other supported extensions -> run their converters.
    The conversion will depend on the type of biosignal selected in main_window.selected_experiment

    """
    valid_files = []
    converted_count = 0
    accepted_count = 0
    skipped_count = 0
    total = len(files)
    available_experiments_to_convert = ["EEG", "ECG"]

    # Detect type of experiment
    experiment_type = getattr(main_window, "selected_experiment", None).split('_')[0].upper()
    if experiment_type not in available_experiments_to_convert:
        _log_message(log_browser, f"⚠️ Experiment type '{experiment_type}' not supported.")
        return []

    # Ask for output directory
    output_dir = QtWidgets.QFileDialog.getExistingDirectory(
        None,
        "Select destination folder for converted files (semi-BIDS root)"
    )
    if not output_dir:
        _log_message(log_browser, "🚫 Conversion cancelled (no output folder selected).")
        return []

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = output_dir / "tmp_conversion"
    tmp_dir.mkdir(exist_ok=True)
    _log_message(log_browser, f"📁 Output path selected: {output_dir}")

    # ECG: skip conversion, just reorganize files (maybe in the future we have to modify it)
    if experiment_type == "ECG":
        _log_message(log_browser, "🫀 ECG experiment detected — not conversion needed, organizing in semi-BIDS.")
        try:
            input_dir = os.path.dirname(files[0])
            convert_to_semi_bids(input_dir, output_dir, 'ecg')
            _log_message(log_browser, "✅ ECG semi-BIDS organization completed successfully.")
        except Exception as e:
            _log_message(log_browser, f"❌ Error organizing ECG semi-BIDS: {e}")
        return []

    # EEG: perform conversion, save in new path, then organize
    for i, file in enumerate(files):
        filename = os.path.basename(file)

        # find the registered converter extension (first match)
        matched_ext = next((ext for ext in CONVERTERS.keys() if file.endswith(ext)), None)

        if matched_ext is None:
            # unsupported file type
            skipped_count += 1
            _log_message(
                log_browser,
                f"⚠️ <b>{filename}</b> → <span style='color:orange;'>Unsupported file type.</span>"
            )
            _update_progress(progress_bar, i, total)
            continue

        converter = CONVERTERS[matched_ext]["converter"]

        # Special-case for already-REC files: check if they need normalization
        if matched_ext == ".rec.bson":
            try:
                data = Recording.load(file)
            except Exception as e:
                _log_message(log_browser, f"❌ <b>{filename}</b> → Error loading .rec.bson: {e}")
                _update_progress(progress_bar, i, total)
                continue

            # If data.marks exists (and is not None) we skip conversion
            if hasattr(data, "marks") and data.marks is not None:
                # Already correct: copy to tmp and skip conversion
                dest_file = tmp_dir / Path(file).name
                shutil.copy2(file, dest_file)
                valid_files.append(str(dest_file))
                accepted_count += 1
                _log_message(log_browser, f"ℹ️ {filename} → Already contains 'marks', no normalization needed.")
                _update_progress(progress_bar, i, total)
                continue
            else:
                _log_message(log_browser, f"⚙️ {filename} → Missing 'marks', normalizing...")
                try:
                    new_file = _run_converter(converter, file, log_browser, output_dir=tmp_dir)
                    valid_files.append(str(new_file))
                    converted_count += 1
                    _log_message(log_browser, f"✅ {filename} → Normalized successfully.")
                except Exception as e:
                    _log_message(log_browser, f"❌ {filename} → Error normalizing: {e}")
                _update_progress(progress_bar, i, total)
                continue

        # Run the converter
        # ---- Other types (.rcp.bson, .mat, etc.) ----
        try:
            _log_message(log_browser, f"⚙️ {filename} → Starting conversion...")
            new_file = _run_converter(converter, file, log_browser, output_dir=tmp_dir)
            if not new_file or not os.path.exists(new_file):
                _log_message(log_browser, f"❌ {filename} → Converter returned no valid path.")
                continue

            dest_file = tmp_dir / Path(file).name.replace(' ', '_')
            dest_file = dest_file.with_suffix(".rec.bson")
            shutil.copy2(new_file, dest_file)
            valid_files.append(str(dest_file))
            converted_count += 1

            _log_message(log_browser, f"✅ {filename} → Conversion successful.")
        except Exception as e:
            _log_message(log_browser, f"❌ {filename} → Error during conversion: {e}")

        _update_progress(progress_bar, i, total)

    # ---- SEMI-BIDS ORGANIZATION ----
    semi_bids_files = []
    if valid_files:
        try:
            _log_message(log_browser, "📂 Organizing converted files into semi-BIDS structure...")
            semi_bids_files  = convert_to_semi_bids(tmp_dir, output_dir, 'eeg')
            _log_message(log_browser, "✅ EEG semi-BIDS organization completed successfully.")
        except Exception as e:
            _log_message(log_browser, f"❌ Error organizing semi-BIDS: {e}")

    # Cleanup
    try:
        shutil.rmtree(tmp_dir)
        _log_message(log_browser, "🧹 Temporary conversion folder removed.")
    except Exception:
        _log_message(log_browser, "⚠️ Could not remove temporary folder (in use?).")

    # ---- Summary ----
    summary = (
        "<hr><b>Summary:</b><br>"
        f"🟢 Converted: {converted_count} file(s)<br>"
        f"🔵 Accepted (already correct): {accepted_count} file(s)<br>"
    )
    if skipped_count > 0:
        summary += f"⚠️ Skipped: {skipped_count} file(s)"
    _log_message(log_browser, summary)

    return [str(f) for f in semi_bids_files]
