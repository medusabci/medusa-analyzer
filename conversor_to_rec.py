import os
import numpy as np
import medusa.bci.erp_spellers
from medusa.components import Recording, CustomExperimentData
from PyQt5 import QtWidgets


def conversor_to_rec(files, progress_bar=None, log_browser=None, return_rec_paths=True):
    """
        Convert different types of MEDUSA Files to .rec format
    """
    total = len(files)
    converted_paths = []
    skipped_count = 0

    # For each file...
    for i, file in enumerate(files):
        filename = os.path.basename(file)

        # Logic to convert from RCP to REC
        if file.endswith(".rcp.bson"):
            try:
                # If logging is activated...
                if log_browser:
                    log_browser.append(f"⚙️ <b>{filename}</b> → Starting conversion...")
                    QtWidgets.QApplication.processEvents()

                # Load the files
                recording = Recording.load(file)
                # Get the marks for events
                marks = CustomExperimentData()
                marks.events_labels = recording.erpspellerdata.erp_labels.tolist() \
                    if isinstance(recording.erpspellerdata.erp_labels, np.ndarray) \
                    else recording.erpspellerdata.erp_labels
                marks.events_times = recording.erpspellerdata.onsets.tolist() \
                    if isinstance(recording.erpspellerdata.onsets, np.ndarray) \
                    else recording.erpspellerdata.onsets
                marks.app_settings = {
                    'events': {'target': {'label': 0}, 'non_target': {'label': 1}},
                    'conditions': {'full': {'label': 0}}
                }
                # And for conditions
                marks.conditions_labels = []
                marks.conditions_times = np.empty((0, 2))

                # Store the marks in the new REC file
                recording.add_experiment_data(marks, key='marks')
                new_file = file.replace(".rcp.bson", ".rec.bson")
                recording.save(new_file)
                converted_paths.append(new_file)

                # Logging
                if log_browser:
                    log_browser.append(f"✅ <b>{filename}</b> → <span style='color:green;'>Conversion successful</span>")

            # Exception handler
            except Exception as e:
                if log_browser:
                    log_browser.append(f"❌ <b>{filename}</b> → <span style='color:red;'>Error:</span> {str(e)}")

            # If progress bar is activated...
            if progress_bar:
                progress_bar.setValue(int((i + 1) / total * 100))
                QtWidgets.QApplication.processEvents()

        else: # Other (non-supported) formats
            skipped_count += 1
            if log_browser:
                log_browser.append(
                    f"⚠️ <b>{filename}</b> → <span style='color:orange;'>Unsupported file type.</span><br>"
                    f"This format is not yet available for conversion and will be ignored."
                )
                QtWidgets.QApplication.processEvents()
            continue

    # If logging is activated...
    if log_browser:
        summary = f"<hr><b>Summary:</b><br>✅ Converted: {len(converted_paths)} file(s)"
        if skipped_count > 0:
            summary += f"<br>⚠️ Skipped (unsupported): {skipped_count} file(s)"
        log_browser.append(summary)
        QtWidgets.QApplication.processEvents()

    if return_rec_paths:
        return converted_paths

# import os
# import numpy as np
# import medusa.bci.erp_spellers
# from medusa.components import Recording, CustomExperimentData
#
# files = [r'D:\Proyectos\medusa-analyzer\data\data_braingym\U01-control-r1.rcp.bson']
#
# import os
# import numpy as np
# import medusa.bci.erp_spellers
# from medusa.components import Recording, CustomExperimentData
#
# files = [r'D:\Proyectos\medusa-analyzer\data\data_braingym\U01-control-r1.rcp.bson']
#
# def conversor_to_rec(files):
#     new_files = []
#
#     for file in files:
#         if file.endswith(".rcp.bson"):
#             recording = Recording.load(file)
#
#             marks = CustomExperimentData()
#             marks.events_labels = recording.erpspellerdata.erp_labels.tolist() \
#                 if isinstance(recording.erpspellerdata.erp_labels, np.ndarray) \
#                 else recording.erpspellerdata.erp_labels
#
#             marks.events_times = recording.erpspellerdata.onsets.tolist() \
#                 if isinstance(recording.erpspellerdata.onsets, np.ndarray) \
#                 else recording.erpspellerdata.onsets
#
#             # Configuración de eventos y condiciones ficticias
#             marks.app_settings = {
#                 'events': {
#                     'target': {'label': 0},
#                     'non_target': {'label': 1}
#                 },
#                 'conditions': {
#                     'full': {'label': 0}
#                 }
#             }
#
#             marks.conditions_labels = []
#             marks.conditions_times = np.empty((0, 2))
#
#             recording.add_experiment_data(marks, key='marks')
#
#             new_file = file.replace(".rcp.bson", ".rec.bson")
#             recording.save(new_file)
