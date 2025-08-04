import os
import numpy as np
import medusa.bci.erp_spellers
from medusa.components import Recording, CustomExperimentData
from PyQt5 import QtWidgets


def conversor_to_rec(files, progress_bar=None, log_browser=None, return_rec_paths=True):
    total = len(files)
    converted_paths = []
    skipped_count = 0

    for i, file in enumerate(files):
        filename = os.path.basename(file)

        if not file.endswith(".rcp.bson"):
            skipped_count += 1
            if log_browser:
                log_browser.append(
                    f"⚠️ <b>{filename}</b> → <span style='color:orange;'>Unsupported file type.</span><br>"
                    f"This format is not yet available for conversion and will be ignored."
                )
                QtWidgets.QApplication.processEvents()
            continue

        try:
            if log_browser:
                log_browser.append(f"⚙️ <b>{filename}</b> → Starting conversion...")
                QtWidgets.QApplication.processEvents()

            recording = Recording.load(file)

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

            marks.conditions_labels = []
            marks.conditions_times = np.empty((0, 2))

            recording.add_experiment_data(marks, key='marks')

            new_file = file.replace(".rcp.bson", ".rec.bson")
            recording.save(new_file)
            converted_paths.append(new_file)

            if log_browser:
                log_browser.append(f"✅ <b>{filename}</b> → <span style='color:green;'>Conversion successful</span>")

        except Exception as e:
            if log_browser:
                log_browser.append(f"❌ <b>{filename}</b> → <span style='color:red;'>Error:</span> {str(e)}")

        if progress_bar:
            progress_bar.setValue(int((i + 1) / total * 100))
            QtWidgets.QApplication.processEvents()

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
