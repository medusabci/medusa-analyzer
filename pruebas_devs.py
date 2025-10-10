import medusa
from eeg_features.utils import run_pipeline
import json
from medusa import ecg

file = r'C:\Users\beapa\PycharmProjects\medusa-analyzer\Signals\R9.rec.bson'
file2 = r'C:\Users\beapa\PycharmProjects\medusa-analyzer\Signals\R3.rec.bson'

with open("settings.json", "r", encoding="utf-8") as f:
    settings = json.load(f)

data = medusa.components.Recording.load(file)
data2 = medusa.components.Recording.load(file2)



run_pipeline([], settings, 3)
