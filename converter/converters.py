from medusa.components import Recording, CustomExperimentData
from medusa.meeg.meeg import EEG, EEGChannelSet
import csv
import numpy as np
import pandas as pd
import scipy.io as sio

# ----------------------------- CONVERTERS -----------------------------
def _convert_rec_file(file, output_dir, worker=None):
    """
    Normalize REC file: ensure it always contains a 'marks' entry.
    """
    base_name = file.name # It is not necessary to change the extension

    try:
        subj_id = output_dir.stem.split('.')[0]

        # Load the recording
        recording = Recording.load(subject_id=subj_id)
        # Check if 'marks' attribute exists
        if not hasattr(recording, "marks") or recording.marks is None:
            marks = _create_empty_marks()
            recording.add_experiment_data(marks, key="marks")
        # Save the normalized recording
        bids_folders = output_dir.parent
        bids_folders.mkdir(parents=True, exist_ok=True)
        recording.save(str(output_dir))
        return str(output_dir)
    except Exception as e:
        if worker:
            worker.log.emit(f"❌ Error converting REC file: {e}")
        return None


def _convert_rcp_file(file, output_dir, worker=None):
    """
    Convert RCP file to REC format.
    """
    base_name = file.name.replace(".rcp.bson", ".rec.bson")  # Replace extension from .rcp.bson to .rec.bson

    try:
        # Create Recording object
        subj_id = output_dir.stem.split('.')[0]
        recording = Recording(subject_id=subj_id)
        data = Recording.load(str(file))

        # Extract ERP marks
        marks = CustomExperimentData()
        marks.events_labels = data.erpspellerdata.erp_labels.tolist() if isinstance(data.erpspellerdata.erp_labels, np.ndarray) else data.erpspellerdata.erp_labels
        marks.events_times = data.erpspellerdata.onsets.tolist() if isinstance(data.erpspellerdata.onsets, np.ndarray) else data.erpspellerdata.onsets
        marks.app_settings = {'events': {'target': {'desc-name': 'Target','label': 0}, 'non_target': {'desc-name': 'Non target','label': 1}}, 'conditions': {'no-condition': {'desc-name': 'No condition','label': 0}}}
        marks.conditions_labels, marks.conditions_times = [], np.empty((0, 2))

        # Fill the Recording object
        for biosignal in data.biosignals.values():
            # biosignal_type = biosignal['class_name']
            # recording.add_biosignal(**{biosignal_type: biosignal})
            recording.add_biosignal(biosignal=biosignal)
        recording.add_experiment_data(marks, key='marks')
        bids_folders = output_dir.parent
        bids_folders.mkdir(parents=True, exist_ok=True)
        recording.save(str(output_dir))
        return str(output_dir)

    except Exception as e:
        if worker:
            worker.log.emit(f"❌ Error converting RCP file: {e}")
        return None


def _convert_mat_file(file, output_dir, worker=None):
    """Convert MATLAB (.mat) file to REC format."""
    # Create unique output filename inside output_dir
    base_name = file.name.replace(".mat", ".rec.bson") # Replace extension from .mat to .rec.bson

    try:
        subj_id = output_dir.stem.split('.')[0]
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

        bids_folders = output_dir.parent
        bids_folders.mkdir(parents=True, exist_ok=True)
        recording.save(str(output_dir))
        return str(output_dir)
    except Exception as e:
        if worker:
            worker.log.emit(f"❌ Error converting MAT file: {e}")
        return None


def _convert_csv_file(file, output_dir, worker=None):
    """
    Convert RCP file to REC format.
    """
    if "EEG" not in str(file).split('\\')[-1].upper():
        raise TypeError('File skipped - Not a valid EEG file')   # Only process EEG CSV files

    try:
        subj_id = output_dir.stem
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
        annot_id = file.stem.split('.')[0]
        annot_id = annot_id.split("_")[:3]
        annot_id = "_".join(annot_id)

        # Get annotations (same folder, same subject id, and annotations in the filename)
        annotations = [f for f in file.parent.iterdir() if f.is_file()
                          and annot_id in f.name
                          and "annotations" in f.name]
        # If no annotations file found, return None
        if not annotations:
            raise FileNotFoundError("Annotations file not found for this file")
        # We should have only one annotations file
        annot_df = pd.read_csv(annotations[0], delimiter=';')
        annots = annot_df.iloc[:, [1, 2]].to_numpy()
        # # It is not necessary to align annotations to closest timepoints in the times vector (MEDUSA functions will
        # # handle it)
        # idx_annots = np.abs(times[:, None] - annots).argmin(axis=0)
        # annots = times[idx_annots]
        del annot_df

        # Create marks structure
        marks = CustomExperimentData()
        marks.events_labels = []
        marks.events_times = []
        marks.conditions_labels, marks.conditions_times = [0] * annots.shape[0] * 2, annots.flatten().tolist()
        marks.app_settings = {'conditions': {'restful': {'desc-name': 'Restful sleep', 'label': 0}}, 'events': {}}

        # Create EEG object
        eeg = EEG(times=times, signal=data, fs=fs, channel_set=channel_set)

        # Fill and save recording
        recording.add_biosignal(biosignal=eeg)
        recording.add_experiment_data(marks, key='marks')

        bids_folders = output_dir.parent
        bids_folders.mkdir(parents=True, exist_ok=True)
        recording.save(str(output_dir))
        return str(output_dir)

    except Exception as e:
        if worker:
            worker.log.emit(f"❌ Error converting CSV file: {e}")
        return None

# Converter registry
CONVERTERS = {
    ".rcp.bson": [{
            "name": "RCP Files",
            "function": _convert_rcp_file
    }],
    ".mat":[{
            "name": "GIB Mat Files",
            "function": _convert_mat_file
    }],
    ".rec.bson": [{
            "name": "REC Files",
            "function": _convert_rec_file
    }],
    ".csv": [{
            "name": "CSV Sant Joan Files",
            "function": _convert_csv_file
    }],
}

# ----------------------------- END OF CONVERTERS -----------------------------

## Additional utility functions and classes from utils.py for completeness


def _create_empty_marks():
    """Create empty marks structure"""
    marks = CustomExperimentData()
    marks.events_labels = []
    marks.events_times = []
    marks.conditions_labels = []
    marks.conditions_times = np.empty((0, 2))
    marks.app_settings = {'conditions': {}, 'events': {}}
    return marks