from medusa.components import Recording, CustomExperimentData
from medusa.meeg.meeg import EEG, EEGChannelSet
from medusa.ecg import ECG # Do not remove, it is necessary!
import csv
import numpy as np
import pandas as pd
import scipy.io as sio
import shutil
from pathlib import Path


# ----------------------------- HELPER FUNCTIONS -----------------------------
def _sanitize_name(name):
    """Remove spaces, underscores and hyphens from event/condition names."""
    return str(name).replace(' ', '').replace('_', '').replace('-', '')


def _sanitize_app_settings(app_settings):
    """Sanitize keys in app_settings events and conditions (does not modify desc-names)."""
    if not isinstance(app_settings, dict):
        return app_settings
    
    sanitized = {}
    for key, value in app_settings.items():
        if key in ['events', 'conditions'] and isinstance(value, dict):
            sanitized[key] = {}
            for name, val in value.items():
                sanitized_name = _sanitize_name(name)
                sanitized[key][sanitized_name] = val
        else:
            sanitized[key] = value
            
    return sanitized


# ----------------------------- CONVERTERS -----------------------------
def _convert_rec_file(file, output_dir, worker=None):
    """
    Normalize REC file: ensure it always contains a 'marks' entry.
    """

    try:
        subj_id = output_dir.stem.split('.')[0]
        # Load the recording
        recording = Recording.load(str(file))
        bids_folders = output_dir.parent
        bids_folders.mkdir(parents=True, exist_ok=True)

        if hasattr(recording, "marks") and recording.marks is not None:
            if hasattr(recording.marks, 'app_settings'):
                recording.marks.app_settings = _sanitize_app_settings(recording.marks.app_settings)
                recording.save(str(output_dir))
            else:
                shutil.copy2(file, output_dir)
            return 'already_correct'
        else:
            marks = _create_empty_marks()
            recording.add_experiment_data(marks, key="marks")

        # Save the normalized recording
        recording.save(str(output_dir))
        return str(output_dir)
    except Exception as e:
        if worker:
            worker.log.emit(f"❌ Error converting REC file: {e}")
        return None


def _convert_edubiomat_file(file, output_dir, worker=None):
    """
    Normalize REC file: ensure it always contains a 'marks' entry.
    """

    category_map = {}
    category_map[1] = {
        0: "Agr", 1: "DesAgr"}
    category_map[2] = {
        0: "Agr", 1: "DesAgr"}
    category_map[3] = {
        0: "Alg_Con", 1: "Alg_Pic", 2: "Alg_Abs",
        3: "Est_Con", 4: "Est_Pic", 5: "Est_Abs",
        6: "Geo_Con", 7: "Geo_Pic", 8: "Geo_Abs",
        9: "Num_Con", 10: "Num_Pic", 11: "Num_Abs",
    }

    try:
        subj_id = output_dir.stem.split('.')[0]
        # Load the recording
        recording = Recording.load(str(file))
        bids_folders = output_dir.parent
        bids_folders.mkdir(parents=True, exist_ok=True)

        # Extract ERP marks
        marks = CustomExperimentData()
        evt_names = []
        evt_times = []
        for trial in recording.exp_data.data:
            if '-' in  Path(trial['img_path']).stem:
                group_id = Path(trial['img_path']).stem.split('-')[-1]
            else:
                continue
            experiment = int(Path(trial['img_path']).parts[-2])
            response = 'Agr' if trial['response'] == 1 else 'DesAgr'
            evt_names.append(category_map[experiment][int(group_id)] + response)
            evt_times.append(trial['onset_time'])

        # Convert names to labels
        names_map = {x: i for i, x in enumerate(set(evt_names))}
        evt_labels = [names_map[x] for x in evt_names]
        # Create dict for app_settings
        dict_app_settings = {}
        for name, label in names_map.items():
            dict_app_settings[name] = {'desc-name': name.upper().replace('_',' '), 'label': label}

        # Stores the marks
        marks.events_labels = evt_labels
        marks.events_times = evt_times
        # Store the app settings
        marks.app_settings = _sanitize_app_settings({
            'events': dict_app_settings,
            'conditions': {'no-condition': {'desc-name': 'No condition', 'label': 0}}
        })
        marks.conditions_labels, marks.conditions_times = [], np.empty((0, 2))
        # Add the marks to the recording
        recording.add_experiment_data(marks, key="marks")

        # Save the normalized recording
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

    try:
        # Create Recording object
        subj_id = output_dir.stem.split('.')[0]
        recording = Recording(subject_id=subj_id)
        data = Recording.load(str(file))

        # Extract ERP marks
        marks = CustomExperimentData()
        marks.events_labels = data.erpspellerdata.erp_labels.tolist() if isinstance(data.erpspellerdata.erp_labels, np.ndarray) else data.erpspellerdata.erp_labels
        marks.events_times = data.erpspellerdata.onsets.tolist() if isinstance(data.erpspellerdata.onsets, np.ndarray) else data.erpspellerdata.onsets
        marks.app_settings = _sanitize_app_settings({
            'events': {'non_target': {'desc-name': 'Non target', 'label': 0}, 'target': {'desc-name': 'Target', 'label': 1}},
            'conditions': {'no-condition': {'desc-name': 'No condition', 'label': 0}}
        })
        marks.conditions_labels, marks.conditions_times = [], np.empty((0, 2))

        # Fill the Recording object
        for biosignal in data.biosignals.values():
            recording.add_biosignal(biosignal= getattr(data, biosignal['class_name'].lower()))
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
        marks.app_settings = _sanitize_app_settings({
            'conditions': {'restful': {'desc-name': 'Restful sleep', 'label': 0}},
            'events': {}
        })

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


def _convert_mne(file, output_dir, worker=None):
    import mne
    """
    Convert MNE file to REC format.
    """
    try:
        subj_id = output_dir.stem
        recording = Recording(subject_id=subj_id)

        # Load data
        mne_data = mne.io.read_raw(file, preload=False)

        data = mne_data.get_data().T
        fs = mne_data.info['sfreq']
        times = mne_data.times
        channels = mne_data.info['ch_names']

        # Create the channel set
        if any(t in ['mag', 'grad'] for t in mne_data.get_channel_types()): # If MEG
            channels = [{"label": f"{ch}", "coord": "all", "reference": None}
                        for ch in channels]
            channel_set = EEGChannelSet(reference_method="average")
            channel_set.set_montage(channels=channels, allow_unlocated_channels=True)

        else:  # If EEG
            channel_set = EEGChannelSet()
            channel_set.set_standard_montage(l_cha=channels, montage='10-05')

        # Extract marks from MNE
        marks = CustomExperimentData()

        # Events
        evt_annotations = mne_data.annotations.duration < 0.01
        evt_names = mne_data.annotations.description[evt_annotations]
        evt_times = mne_data.annotations.onset[evt_annotations]
        # Convert names to labels
        names_map = {x: i for i, x in enumerate(set(evt_names))}
        evt_labels = [names_map[x] for x in evt_names]
        # Create dict for app_settings
        dict_app_settings_evt = {}
        for name, label in names_map.items():
            dict_app_settings_evt[name] = {'desc-name': name, 'label': label}
        # Store the marks
        marks.events_labels = evt_labels
        marks.events_times = evt_times

        # Conditions
        cnd_names = mne_data.annotations.description[~evt_annotations]
        cnd_times = mne_data.annotations.onset[~evt_annotations]
        cnd_times_off = mne_data.annotations.onset[~evt_annotations] + mne_data.annotations.duration[~evt_annotations]
        cnd_times = np.column_stack((cnd_times, cnd_times_off)).flatten().tolist()
        # Convert names to labels
        names_map = {x: i for i, x in enumerate(set(cnd_names))}
        cnd_labels = [names_map[x] for x in cnd_names]
        # Create dict for app_settings
        dict_app_settings_cnd = {}
        for name, label in names_map.items():
            dict_app_settings_cnd[name] = {'desc-name': name, 'label': label}
        # Store the marks
        marks.conditions_labels = cnd_labels
        marks.conditions_times = cnd_times

        # Store the app settings
        marks.app_settings = _sanitize_app_settings({
            'events': dict_app_settings_evt,
            'conditions': dict_app_settings_cnd
        })

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
            "name": "RCP",
            "function": _convert_rcp_file
    }],
    ".mat":[{
            "name": "GIB Mat",
            "function": _convert_mat_file
    }],
    ".rec.bson": [
        {
            "name": "Recorder REC",
            "function": _convert_rec_file
        },
        {
            "name": "EDUBIOMAT BSON",
            "function": _convert_edubiomat_file
    }],
    ".csv": [{
            "name": "CSV Sant Joan",
            "function": _convert_csv_file
    }],
    ".rec.mat": [{
            "name": "EDUBIOMAT Mat",
            "function": _convert_edubiomat_file
    }],
    ".*": [{
        "name": "MNE-Compatible format",
        "function": _convert_mne
    }]
}

MNE_FORMATS = (
    '.fif', '.fif.gz',
    '.set', '.fdt',            # EEGLAB
    '.bdf',                    # Biosemi BDF
    '.edf',                    # EDF / EDF+
    '.vhdr', '.vmrk', '.eeg',  # BrainVision (header/markers/raw)
    '.cnt',                    # Neuroscan CNT
    '.mff', '.egi',            # EGI (MFF / simple binary)
    '.gdf',                    # GDF
    '.sqd',                    # KIT (sqd)
    '.ds',                     # CTF directory (CTF .ds)
    '.nedf',                   # NeuroElectrics NEDF
    '.ns1', '.ns2', '.ns3', '.ns4', '.ns5', '.ns6',  # Blackrock NSx variants
    '.ncs',                    # Neuralynx (.ncs files)
    '.mat',                    # FieldTrip / MATLAB structures
    '.fil',                    # FIL-OPMEG
    '.lay', '.dat',            # Persyst (.lay/.dat)
    '.asc',                    # Eyelink (.asc)
    '.snirf',                  # SNIRF (nirs)
)
# ----------------------------- END OF CONVERTERS -----------------------------

## Additional utility functions and classes from utils.py for completeness


def _create_empty_marks():
    """Create empty marks structure"""
    marks = CustomExperimentData()
    marks.events_labels = []
    marks.events_times = []
    marks.conditions_labels = []
    marks.conditions_times = np.empty((0, 2))
    marks.app_settings = _sanitize_app_settings({'conditions': {}, 'events': {}})
    return marks
