import os
import numpy as np
import medusa.bci.erp_spellers
from medusa.components import Recording, CustomExperimentData

files = [r'D:\Proyectos\medusa-analyzer\data\data_braingym\U01-control-r1.rcp.bson']

import os
import numpy as np
import medusa.bci.erp_spellers
from medusa.components import Recording, CustomExperimentData

files = [r'D:\Proyectos\medusa-analyzer\data\data_braingym\U01-control-r1.rcp.bson']

def conversor_to_rec(files):
    new_files = []

    for file in files:
        if file.endswith(".rcp.bson"):
            recording = Recording.load(file)

            marks = CustomExperimentData()
            marks.events_labels = recording.erpspellerdata.erp_labels.tolist() \
                if isinstance(recording.erpspellerdata.erp_labels, np.ndarray) \
                else recording.erpspellerdata.erp_labels

            marks.events_times = recording.erpspellerdata.onsets.tolist() \
                if isinstance(recording.erpspellerdata.onsets, np.ndarray) \
                else recording.erpspellerdata.onsets

            # Configuración de eventos y condiciones ficticias
            marks.app_settings = {
                'events': {
                    'target': {'label': 0},
                    'non_target': {'label': 1}
                },
                'conditions': {
                    'full': {'label': 0}
                }
            }

            marks.conditions_labels = []
            marks.conditions_times = np.empty((0, 2))

            recording.add_experiment_data(marks, key='marks')

            new_file = file.replace(".rcp.bson", ".rec.bson")
            recording.save(new_file)
