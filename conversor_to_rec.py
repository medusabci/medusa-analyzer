import os
import medusa.bci.erp_spellers
from medusa.components import Recording, CustomExperimentData

files = [r'D:\Proyectos\medusa-analyzer\data\data_braingym\U01-control-r1.rcp.bson']

def conversor_to_rec(files):
    new_files = []

    for file in files:
        if file.endswith(".rcp.bson"):
            recording = Recording.load(file)

            # Crear instancia de CustomExperimentData y asignar atributos
            marks = CustomExperimentData()
            marks.app_settings = {
                'events': {
                    'target': {'label': 0},
                    'non_target': {'label': 1}
                },
                'conditions': {}
            }
            marks.condition_labels = []
            marks.condition_times = []
            marks.event_labels = recording.erpspellerdata.erp_labels
            marks.event_times = recording.erpspellerdata.onsets

            recording.marks = marks

            new_file = file.replace(".rcp.bson", ".rec.bson")
            recording.save(new_file)
            new_files.append(new_file)