import os
from medusa.components import Recording, CustomExperimentData
import re
import shutil
from pathlib import Path
import numpy as np
import scipy.io as sio
from medusa.meeg.meeg import EEG, EEGChannelSet
from PySide6.QtCore import QThread, Signal
import csv
import pandas as pd


# README: To include a new converter, just create a function that takes a file path as input (e.g.
# _convert_newformat_file(filepath,output_dir,worker=None)) and returns the new filepath, and include it in the CONVERTERS dictionary with the
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


def _log_conversion_summary(counters, worker):
    """Print final summary."""
    summary = (
        "<hr><b>Summary:</b><br>"
        f"🟢 Converted: {counters['converted']} file(s)<br>"
        f"🔵 Accepted (already correct): {counters['accepted']} file(s)<br>"
    )
    if counters["skipped"]:
        summary += f"⚠️ Skipped: {counters['skipped']} file(s)"
    worker.log.emit(summary)


def _cleanup_tmp_folder(tmp_dir, worker):
    """Remove temporary folder safely."""
    try:
        shutil.rmtree(tmp_dir)
        worker.log.emit("🧹 Temporary conversion folder removed.")
    except Exception:
        worker.log.emit("⚠️ Could not remove temporary folder (in use?).")


# ----------------------------- ADDITIONAL FUNCTIONS -----------------------------
def process_file(file, filename, tmp_dir, converter, worker, matched_ext, root_dir):
    # Get the output path with the original folder structure
    file_path = Path(file)
    # File path relative to root_dir
    relative = file_path.relative_to(Path(root_dir))
    folder_structure = relative.parent  # Discard the filename to keep the relative folder structure
    tmp_dir_complete = Path(tmp_dir) / folder_structure  # Include the folder structure in the tmp_dir
    tmp_dir_complete = Path(tmp_dir_complete)
    tmp_dir_complete.mkdir(parents=True, exist_ok=True)


    if matched_ext == ".rec.bson": # Check if the rec.bson file is valid
        """Handle existing .rec.bson files."""
        try:
            data = Recording.load(file)
        except Exception as e:
            worker.log.emit(f"❌ <b>{filename}</b> → Error loading .rec.bson: {e}")
            return 'skipped'

        if getattr(data, "marks", None):
            shutil.copy2(file, tmp_dir_complete / Path(file).name)
            worker.log.emit(f"ℹ️ {filename} → Already contains 'marks', skipped conversion.")
            return 'accepted'

    worker.log.emit(f"⚙️ {filename} → Converting...")
    try:
        # Run the converter
        new_file = converter(file, tmp_dir_complete, worker)

        if not new_file or not os.path.exists(new_file):
            worker.log.emit(f"❌ {filename} → Converter returned no valid path.")
            return 'skipped'
        else:
            worker.log.emit(f"✅ {filename} → Converting successful.")
            return 'converted'
    except Exception as e:
        worker.log.emit(f"❌ {filename} → Error during conversion: {e}")
        return 'skipped'

# ----------------------------- CONVERTERS -----------------------------
def _convert_rec_file(file, output_dir, worker=None):
    """
    Normalize REC file: ensure it always contains a 'marks' entry.
    """
    file = Path(file)
    base_name = file.name # It is not necessary to change the extension
    converted_file = output_dir / base_name

    try:
        # Load the recording
        recording = Recording.load(str(file))
        # Check if 'marks' attribute exists
        if not hasattr(recording, "marks") or recording.marks is None:
            marks = _create_empty_marks()
            recording.add_experiment_data(marks, key="marks")
        # Save the normalized recording
        recording.save(str(converted_file))
        return str(converted_file)
    except Exception as e:
        if worker:
            worker.log.emit(f"❌ Error converting REC file: {e}")
        return None


def _convert_rcp_file(file, output_dir, worker=None):
    """
    Convert RCP file to REC format.
    """
    file = Path(file)
    base_name = file.name.replace(".rcp.bson", ".rec.bson")  # Replace extension from .rcp.bson to .rec.bson
    converted_file = output_dir / base_name

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
        for biosignal in data.biosignals.values():
            # biosignal_type = biosignal['class_name']
            # recording.add_biosignal(**{biosignal_type: biosignal})
            recording.add_biosignal(biosignal=biosignal)
        recording.add_experiment_data(marks, key='marks')
        recording.save(str(converted_file))
        return str(converted_file)

    except Exception as e:
        if worker:
            worker.log.emit(f"❌ Error converting RCP file: {e}")
        return None


def _convert_mat_file(file, output_dir, worker=None):
    """Convert MATLAB (.mat) file to REC format."""
    file = Path(file)
    # Create unique output filename inside output_dir
    base_name = file.name.replace(".mat", ".rec.bson") # Replace extension from .mat to .rec.bson
    converted_file = output_dir / base_name

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

        recording.save(str(converted_file))
        return str(converted_file)
    except Exception as e:
        if worker:
            worker.log.emit(f"❌ Error converting MAT file: {e}")
        return None


def _convert_csv_file(file, output_dir, worker=None):
    """
    Convert RCP file to REC format.
    """
    if "EEG" not in file.split('\\')[-1].upper():
        return None  # Only process EEG CSV files

    file = Path(file)
    base_name = file.name.replace(".csv", ".rec.bson")  # Replace extension from .rcp.bson to .rec.bson
    converted_file = output_dir / base_name

    try:
        subj_id = file.stem.split('.')[0]
        subj_id = subj_id.split("_")[:3]
        subj_id = "_".join(subj_id)
        recording = Recording(subject_id=subj_id)
        # Load MATLAB data
        with open(file, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            signal = np.array(list(reader), dtype=float)

        data = signal[:,1]
        data = data.reshape(-1,1)  # Reshape to 2D array
        del signal
        fs = 200
        times = np.linspace(0, data.shape[0] / fs, data.shape[0], endpoint=False)

        # Create the channel set
        channel_set = EEGChannelSet(reference_method="average")
        channel_set.set_montage(channels=[{"label": "EEG1", "coord": "all", "reference": None}], allow_unlocated_channels=True)

        # Create the marks from annotations file

        # Get annotations (same folder, same subject id, and annotations in the filename)
        annotations = [f for f in file.parent.iterdir() if f.is_file()
                          and subj_id in f.name
                          and "annotations" in f.name]
        # If no annotations file found, return None
        if not annotations:
            print("Annotations file not found.")
            return None
        # We should have only one annotations file
        annot_df = pd.read_csv(annotations[0], delimiter=';')
        annots = annot_df.iloc[:, [1, 2]].to_numpy()
        del annot_df

        # Create marks structure
        marks = CustomExperimentData()
        marks.events_labels = []
        marks.events_times = []
        marks.conditions_labels, marks.conditions_times = [0] * annots.shape[0], annots
        marks.app_settings = {'conditions': {'restful': {'label': 0}}, 'events': {}}

        # Create EEG object
        eeg = EEG(times=times, signal=data, fs=fs, channel_set=channel_set)

        # Fill and save recording
        recording.add_biosignal(biosignal=eeg)
        recording.add_experiment_data(marks, key='marks')

        recording.save(str(converted_file))
        return str(converted_file)

    except Exception as e:
        if worker:
            worker.log.emit(f"❌ Error converting MAT file: {e}")
        return None

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
    },
    ".csv": {
        "converter": _convert_csv_file
    }
}

# ----------------------------- BIDS -----------------------------
def convert_to_bids(input_path, output_path, anat, worker):
    """
    Organize recordings into a BIDS structure.

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
    worker.log.emit("📂 Organizing converted files into BIDS structure...")

    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    all_final_files = []

    try:
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
                    files_from_process = move_recordings(ses_dir, ses_bids_path, anat, record_pattern)
                    all_final_files.extend(files_from_process)
            else:
                # No sessions detected → process subject root directly
                files_from_process = move_recordings(subj_dir, subj_bids_path, anat, record_pattern)
                all_final_files.extend(files_from_process)

        worker.log.emit("✅ BIDS organization completed successfully.")
        return all_final_files

    except Exception as e:
        worker.log.emit(f"❌ Error organizing BIDS: {e}")
        return []

def move_recordings(source_dir, dest_root, anat, record_pattern):
    """
    Process all .rec.bson files in a directory and copy them into the BIDS structure.
    """

    # Folder with the biosignal type (i.e. EEG, ECG)
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

    def __init__(self, files, experiment, output_dir, root_dir):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.experiment = experiment
        self.root_dir = root_dir

    def run(self):
        """Runs run_pipeline in a separate thread and emits finished signal when done."""
        error_found = False
        try:
            # Call the main pipeline function
            converted_files = self.converter_main(self.files, self.experiment, self.output_dir, self.root_dir)
        except Exception as e: # if error
            self.log.emit(f"Error in conversion: {e}")
            converted_files = []
            error_found = True
        self.finished.emit(converted_files, error_found)

    def converter_main(self, files, experiment, output_dir, root_dir):
        """
        Convert different file types to .rec.bson format and arrange them in BIDS structure.
        - If a file is .rec.bson and already contains data.marks -> skip.
        - If a file is .rec.bson and lacks data.marks -> run the normalizer converter.
        - For other supported extensions -> run their converters.
        """

        if not output_dir:
            return []

        tmp_dir = output_dir / "TMP"
        tmp_dir.mkdir(exist_ok=True)

        counters = {"converted": 0, "accepted": 0, "skipped": 0}
        total = len(files) + 1 # +1 to account for BIDS conversion step

        for i, file in enumerate(files):
            filename = os.path.basename(file)
            matched_ext = next((ext for ext in CONVERTERS if file.endswith(ext)), None)

            if matched_ext is None:
                counters["skipped"] += 1
                self.log.emit(f"⚠️ <b>{filename}</b> → Unsupported file type.")
                self.progress.emit(int((i + 1) / total * 100))
                continue

            converter = CONVERTERS[matched_ext]["converter"]

            result = process_file(file, filename, tmp_dir, converter, self, matched_ext, root_dir)
            counters[result] += 1

            self.progress.emit(int((i + 1) / total * 100))

        bids_files = convert_to_bids(tmp_dir, output_dir, experiment, self)
        self.progress.emit(100)
        _cleanup_tmp_folder(tmp_dir, self)
        _log_conversion_summary(counters, self)
        converted_files = [str(f) for f in bids_files]
        return converted_files
