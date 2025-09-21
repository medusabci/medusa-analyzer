import os
from PySide6 import QtWidgets
import scipy.io as sio
from medusa.meeg.meeg import *
from medusa.components import Recording, CustomExperimentData
from medusa.bci import erp_spellers
from medusa import ecg
# README: To include a new converter, just create a function that takes a file path as input (e.g.
# _convert_newformat_file(filepath)) and returns the new filepath, and include it in the CONVERTERS dictionary with the
# corresponding file extension.

# TODO : GESTIONAR DIFERENTES BIOSIGNALS


def _convert_rcp_file(file):
    """Convert RCP file to REC format"""
    # Create the Recording object
    subj_id = file.split('/')[0].split('.')
    recording = Recording(subject_id=subj_id)

    # Load the files
    data = Recording.load(file)

    # Get the marks for events
    marks = CustomExperimentData()
    marks.events_labels = data.erpspellerdata.erp_labels.tolist() \
        if isinstance(data.erpspellerdata.erp_labels, np.ndarray) \
        else data.erpspellerdata.erp_labels
    marks.events_times = data.erpspellerdata.onsets.tolist() \
        if isinstance(data.erpspellerdata.onsets, np.ndarray) \
        else data.erpspellerdata.onsets
    marks.app_settings = {
        'events': {'target': {'label': 0}, 'non_target': {'label': 1}},
        'conditions': {'no-condition': {'label': 0}}
    }
    marks.conditions_labels = []
    marks.conditions_times = np.empty((0, 2))

    # Fill the Recording object
    recording.add_biosignal(biosignal=data.eeg)
    recording.add_experiment_data(marks, key='marks')

    # save and return new file path
    new_file = file.replace(".rcp.bson", ".rec.bson")
    recording.save(new_file)
    return new_file


def _convert_mat_file(file):
    """Convert MAT file to REC format"""
    # Create the Recording object
    subj_id = file.split('/')[0].split('.')
    recording = Recording(subject_id=subj_id)

    # Load the files
    mat = sio.loadmat(file, struct_as_record=False, squeeze_me=True)
    data = mat["data"]

    # Empty marks
    marks = _create_empty_marks()

    # Channel set
    if "SOURCES" in file:
        ROIs = [
            {
                "label": f"ROI_{i+1}",
                "coord": "all",
                "reference": None
            }
            for i in range(data.signal.shape[1])
        ]
        channel_set = EEGChannelSet(reference_method="average")
        channel_set.set_montage(channels=ROIs, allow_unlocated_channels=True)
    elif "MEG" in file:
        channels = [
            {
                "label": f"MEG_{i + 1}",
                "coord": "all",
                "reference": None
            }
            for i in range(data.signal.shape[1])
        ]
        channel_set = EEGChannelSet(reference_method="average")
        channel_set.set_montage(channels=channels, allow_unlocated_channels=True)
    else: # Default behaviour: assume EEG
        channels = data.cfg.channels
        replacements = {'T3': 'T7', 'T4': 'T8', 'T5': 'P7', 'T6': 'P8'}
        replace_func = np.vectorize(lambda x: replacements.get(x, x))
        channels = replace_func(channels)
        channel_set = EEGChannelSet()
        channel_set.set_standard_montage(l_cha=channels, montage='10-05')

    # Create the times vector
    times = np.linspace(0, data.signal.shape[0]/ data.cfg.fs, data.signal.shape[0], endpoint=False)

    # Create the EEG object
    eeg = EEG(times=times, signal=data.signal, fs=data.cfg.fs, channel_set=channel_set)

    # Fill the Recording object
    recording.add_biosignal(biosignal=eeg)
    recording.add_experiment_data(marks, key='marks')

    # save and return new file path
    new_file = file.replace(".mat", ".rec.bson")
    recording.save(new_file)
    return new_file

def _convert_rec_file(file, log_browser=None):
    """
    Normalize REC file: ensure it always contains an 'marks' entry.
    """
    # Load the recording
    data = Recording.load(file)

    # Check if 'marks' attribute exists
    if not hasattr(data, "marks") or data.marks is None:
        marks = _create_empty_marks()
        data.add_experiment_data(marks, key="marks")
        data.save(file)  # Overwrite the same file

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


def _run_converter(converter, file, log_browser=None):
    """
    Try to run converter(file, log_browser). If the converter doesn't accept
    the extra arg, fallback to converter(file).
    Return the converter result (path) or None if it fails.
    """
    try:
        return converter(file, log_browser)
    except TypeError:
        return converter(file)


def conversor_to_rec(files, progress_bar=None, log_browser=None):
    """
    Convert different file types to .rec.bson format.
    - If a file is .rec.bson and already contains data.marks -> skip.
    - If a file is .rec.bson and lacks data.marks -> run the normalizer converter.
    - For other supported extensions -> run their converters.
    """
    valid_files = []
    converted_count = 0
    accepted_count = 0
    skipped_count = 0
    total = len(files)

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
                _log_message(log_browser, f"ℹ️ <b>{filename}</b> → Already contains 'marks', skipping.")
                valid_files.append(file)
                accepted_count += 1
                _update_progress(progress_bar, i, total)
                continue

            # otherwise fall through to normalization via converter
            _log_message(log_browser, f"⚙️ <b>{filename}</b> → Missing 'marks', normalizing...")

        else:
            _log_message(log_browser, f"⚙️ <b>{filename}</b> → Starting conversion...")

        # Run the converter
        try:
            new_file = _run_converter(converter, file, log_browser)
            if not new_file:
                _log_message(log_browser, f"❌ <b>{filename}</b> → Converter returned no file path.")
                _update_progress(progress_bar, i, total)
                continue

            valid_files.append(new_file)
            converted_count += 1
            _log_message(
                log_browser,
                f"✅ <b>{os.path.basename(new_file)}</b> → <span style='color:green;'>Conversion successful</span>"
            )
        except Exception as e:
            _log_message(log_browser, f"❌ <b>{filename}</b> → <span style='color:red;'>Error:</span> {e}")

        _update_progress(progress_bar, i, total)

    # Summary logging
    if log_browser:
        summary = "<hr><b>Summary:</b><br>"
        summary += f"🟢 Converted: {converted_count} file(s)<br>"
        summary += f"🔵 Accepted (already correct): {accepted_count} file(s)"
        if skipped_count > 0:
            summary += f"<br>⚠️ Skipped (unsupported): {skipped_count} file(s)"
        _log_message(log_browser, summary)

    return valid_files
