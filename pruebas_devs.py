import medusa
from eeg_features.utils import run_pipeline
import json
from medusa import ecg

clean = r'D:\Proyectos\medusa-analyzer\results_ecg\results\derivatives\preprocessed\sub-16\ecg\sub-16_task-videogame_level-01_lead-II_cond-all.rec.bson'
raw = r'D:\Proyectos\medusa-analyzer\results_ecg\results\derivatives\preprocessed\sub-16\ecg\sub-16_task-videogame_level-01_cond-raw-signal.rec.bson'

with open("settings.json", "r", encoding="utf-8") as f:
    settings = json.load(f)

data = medusa.components.Recording.load(clean)
data2 = medusa.components.Recording.load(raw)



run_pipeline([], settings, 3)
