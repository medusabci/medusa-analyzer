import os
from PySide6 import QtWidgets
from medusa.components import Recording, CustomExperimentData
import re
import shutil
from pathlib import Path
import numpy as np
import scipy.io as sio
from medusa.meeg.meeg import EEG, EEGChannelSet
from medusa.bci import erp_spellers
from medusa import ecg
from PySide6.QtCore import QThread, Signal

# README: To include a new converter, just create a function that takes a file path as input (e.g.
# _convert_newformat_file(filepath)) and returns the new filepath, and include it in the CONVERTERS dictionary with the
# corresponding file extension.

# ----------------------------- UTILITY FUNCTIONS -----------------------------

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


def _handle_ecg_conversion(files, output_dir, tmp_dir, worker):
    """Simplified handler for ECG (no actual conversion)."""
    worker.log.emit("🫀 ECG experiment detected — organizing in semi-BIDS.")
    try:
        input_dir = os.path.dirname(files[0])
        semi_bids_files = convert_to_semi_bids(input_dir, output_dir, 'ecg')
        worker.log.emit("✅ ECG semi-BIDS organization completed successfully.")
    except Exception as e:
        worker.log.emit(f"❌ Error organizing ECG semi-BIDS: {e}")
        return []
    finally:
        _cleanup_tmp(tmp_dir, worker)

    worker.log.emit(f"<hr><b>Summary:</b><br>🔵 Organized files: {len(semi_bids_files)}<br>")
    return [str(f) for f in semi_bids_files]


def _handle_eeg_conversion(files, tmp_dir, output_dir, worker):
    """Handle EEG conversion and organization."""
    valid_files = []
    counters = {"converted": 0, "accepted": 0, "skipped": 0}
    total = len(files)

    for i, file in enumerate(files):
        filename = os.path.basename(file)
        matched_ext = next((ext for ext in CONVERTERS if file.endswith(ext)), None)

        if matched_ext is None:
            counters["skipped"] += 1
            worker.log.emit(f"⚠️ <b>{filename}</b> → Unsupported file type.")
            worker.progress.emit(int((i + 1) / total * 100))
            continue

        converter = CONVERTERS[matched_ext]["converter"]

        if matched_ext == ".rec.bson":
            _process_rec_bson(file, filename, tmp_dir, converter, worker, counters)
        else:
            _process_other_file(file, filename, tmp_dir, converter, worker, counters)

        worker.progress.emit(int((i + 1) / total * 100))

    semi_bids_files = _organize_semi_bids(tmp_dir, output_dir, worker)
    _cleanup_tmp(tmp_dir, worker)
    _log_summary(worker, counters)
    return [str(f) for f in semi_bids_files]


def _process_rec_bson(file, filename, tmp_dir, converter, worker, counters):
    """Handle existing .rec.bson files."""
    try:
        data = Recording.load(file)
    except Exception as e:
        worker.log.emit(f"❌ <b>{filename}</b> → Error loading .rec.bson: {e}")
        return

    if getattr(data, "marks", None):
        shutil.copy2(file, tmp_dir / Path(file).name)
        counters["accepted"] += 1
        worker.log.emit(f"ℹ️ {filename} → Already contains 'marks', skipped conversion.")
    else:
        _convert_and_add(file, filename, converter, tmp_dir, worker, counters, normalize=True)


def _process_other_file(file, filename, tmp_dir, converter, worker, counters):
    """Handle non-.rec.bson files using their converter."""
    _convert_and_add(file, filename, converter, tmp_dir, worker, counters)


def _convert_and_add(file, filename, converter, tmp_dir, worker, counters, normalize=False):
    """Generic conversion logic shared between cases."""
    # action = "Normalizing" if normalize else "Converting"
    action = "Converting"
    worker.log.emit(f"⚙️ {filename} → {action}...")
    try:
        new_file = _run_converter(converter, file, worker, output_dir=tmp_dir)
        if not new_file or not os.path.exists(new_file):
            worker.log.emit(f"❌ {filename} → Converter returned no valid path.")
            return
        dest_file = tmp_dir / Path(file).name.replace(' ', '_')
        dest_file = dest_file.with_suffix(".rec.bson")
        shutil.copy2(new_file, dest_file)
        counters["converted"] += 1
        worker.log.emit(f"✅ {filename} → {action} successful.")
    except Exception as e:
        worker.log.emit(f"❌ {filename} → Error during {action.lower()}: {e}")


def _organize_semi_bids(tmp_dir, output_dir, worker):
    """Organize converted files into semi-BIDS structure."""
    try:
        worker.log.emit("📂 Organizing converted files into semi-BIDS structure...")
        files = convert_to_semi_bids(tmp_dir, output_dir, 'eeg')
        worker.log.emit("✅ EEG semi-BIDS organization completed successfully.")
        return files
    except Exception as e:
        worker.log.emit(f"❌ Error organizing semi-BIDS: {e}")
        return []


def _cleanup_tmp(tmp_dir, worker):
    """Remove temporary folder safely."""
    try:
        shutil.rmtree(tmp_dir)
        worker.log.emit("🧹 Temporary conversion folder removed.")
    except Exception:
        worker.log.emit("⚠️ Could not remove temporary folder (in use?).")


def _log_summary(worker, counters):
    """Print final summary."""
    summary = (
        "<hr><b>Summary:</b><br>"
        f"🟢 Converted: {counters['converted']} file(s)<br>"
        f"🔵 Accepted (already correct): {counters['accepted']} file(s)<br>"
    )
    if counters["skipped"]:
        summary += f"⚠️ Skipped: {counters['skipped']} file(s)"
    worker.log.emit(summary)

# ----------------------------- CONVERTERS -----------------------------
def _convert_rcp_file(file, log_browser=None, output_dir=None):
    """
    Convert RCP file to REC format.
    """
    file = Path(file)
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
        data = Recording.load(str(file))

        # Extract ERP marks
        marks = CustomExperimentData()
        marks.events_labels = data.erpspellerdata.erp_labels.tolist() if isinstance(data.erpspellerdata.erp_labels, np.ndarray) else data.erpspellerdata.erp_labels
        marks.events_times = data.erpspellerdata.onsets.tolist() if isinstance(data.erpspellerdata.onsets, np.ndarray) else data.erpspellerdata.onsets
        marks.app_settings = {'events': {'target': {'label': 0}, 'non_target': {'label': 1}}, 'conditions': {'no-condition': {'label': 0}}}
        marks.conditions_labels, marks.conditions_times = [], np.empty((0, 2))

        # Fill the Recording object
        recording.add_biosignal(biosignal=data.eeg)
        recording.add_experiment_data(marks, key='marks')
        recording.save(str(new_file))
        return str(new_file)

    except Exception as e:
        if log_browser:
            log_browser.append(f"❌ Error converting RCP file: {e}")
        return None


def _convert_mat_file(file, log_browser=None, output_dir=None):
    """Convert MATLAB (.mat) file to REC format."""
    file = Path(file)
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
    Normalize REC file: ensure it always contains a 'marks' entry.
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

# ----------------------------- SEMI BIDS -----------------------------
def convert_to_semi_bids(input_path, output_path, anat):
    """
    Organize recordings into a semi-BIDS structure.

    Example structure:
    output_path/
        ├── sub-01/
        │   └── ses-01/
        │       └── eeg/
        │           ├── sub-01_run-01.rec.bson
        │           ├── sub-01_run-02.rec.bson
        │           └── ...
        ├── sub-02/
        │   └── eeg/
        │       ├── sub-02_run-01.rec.bson
        │       └── ...
        └── ...
    """

    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    all_final_files = []

    # --- Regex patterns for subjects, sessions and runs ---
    subject_pattern = re.compile(r'(?:sujeto[_\s-]*|sub[_\s-]*|s)(\d+)', re.IGNORECASE)
    session_pattern = re.compile(r'(?:sesion[_\s-]*|session[_\s-]*|ses[_\s-]*)(\d+)', re.IGNORECASE)
    record_pattern = re.compile(
        r'(?:run[_\s-]*|r[_\s-]*|recording[_\s-]*|rec[_\s-]*|registro[_\s-]*|ran[_\s-]*)(\d+)',
        re.IGNORECASE
    )

    # --- Detect subjects ---
    # If not folders, we consider the input path as a unique subject
    subj_dirs = [d for d in input_path.iterdir() if d.is_dir()] or [input_path]

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
            # No sessions detected → process subject root directly
            files_from_process = process_recordings(subj_dir, subj_bids_path, anat, record_pattern)
            all_final_files.extend(files_from_process)

    # print(f"✅ Conversion to semi-BIDS completed ({len(all_final_files)} files).")
    return all_final_files

def process_recordings(source_dir, dest_root, anat, record_pattern):
    """
    Process all .rec.bson files in a directory and copy them into the BIDS structure.
    """

    # Folder with the biosignal tyoe (i.e. EEG, ECG)
    anat_dir = dest_root / anat
    anat_dir.mkdir(parents=True, exist_ok=True)

    # Obtain files to process
    rec_files = [f for f in source_dir.iterdir() if f.is_file() and ''.join(f.suffixes).lower().endswith(".rec.bson")]
    if not rec_files:
        return []

    # Get subject id. If not, we consider subject 01 by default.
    subj_match = re.search(r'sub-(\d+)', str(dest_root))
    subj_id = subj_match.group(1) if subj_match else "01"

    final_files = []
    # Loop to rename each file with de BIDS name
    for file in sorted(rec_files):
        rec_match = record_pattern.search(file.name)
        run_id = rec_match.group(1).zfill(2) if rec_match else "01"

        new_name = f"sub-{subj_id}_run-{run_id}.rec.bson"
        dest_file = anat_dir / new_name
        shutil.copy2(file, dest_file)
        final_files.append(dest_file)

    return final_files

# ----------------------------- MAIN ENTRY -----------------------------
# Worker class to run the converter in a separate thread
class ConverterWorker(QThread):
    # Emit when the processing is finished
    finished = Signal(list, bool)
    # For updating the progress bar in the GUI
    progress = Signal(int)
    # For updating log messages in the GUI
    log = Signal(str)

    def __init__(self, files, experiment_type, output_dir):
        super().__init__()
        self.files = files
        self.experiment_type = experiment_type
        self.output_dir = output_dir

    def run(self):
        """Runs run_pipeline in a separate thread and emits finished signal when done."""
        error_found = False
        try:
            # Call the main pipeline function
            converted_files = self.conversor_to_rec(self.files, self.experiment_type, self.output_dir)
        except Exception as e: # if error
            self.log.emit(f"Error in conversion: {e}")
            converted_files = []
            error_found = True
        self.finished.emit(converted_files, error_found)

    def conversor_to_rec(self, files, experiment_type, output_dir):
        """
        Convert different file types to .rec.bson format and arrange them in semi-BIDS structure.
        - If a file is .rec.bson and already contains data.marks -> skip.
        - If a file is .rec.bson and lacks data.marks -> run the normalizer converter.
        - For other supported extensions -> run their converters.
        """

        available_experiments_to_convert = ["EEG", "ECG"]
        if experiment_type not in available_experiments_to_convert:
            self.log.emit(f"⚠️ Experiment type '{experiment_type}' not supported.")
            return []

        if not output_dir:
            return []

        tmp_dir = output_dir / "tmp_conversion"
        tmp_dir.mkdir(exist_ok=True)

        if experiment_type == "ECG":
            return _handle_ecg_conversion(files, output_dir, tmp_dir, self)

        return _handle_eeg_conversion(files, tmp_dir, output_dir, self)
