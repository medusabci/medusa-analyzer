import medusa
from run_pipeline_new import run_pipeline
import json
import numpy as np

file = r'D:\MEDUSA\medusa-analyzer\Signals\R3.rec.bson'


with open("settings.json", "r", encoding="utf-8") as f:
    settings = json.load(f)

data = medusa.components.Recording.load(file)



run_pipeline([], settings, 3)
