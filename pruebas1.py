import medusa
import medusa.components
import medusa.ecg
import numpy as np
from medusa.signal_metrics import multiscale_lempelziv_complexity

# Built-in imports
import math
import ctypes
import os

# External imports
import numpy as np
from scipy.spatial.distance import pdist
from scipy.signal import decimate

# Medusa imports
from medusa.components import ThreadWithReturnValue
from medusa.utils import check_dimensions

file = r"D:\Proyectos\Videojuego\data\S1\R3.rec.bson"
file_1 = r"D:\Proyectos\Videojuego\data\S1\R4.rec.bson"

recording = medusa.components.Recording.load(file)
recording_1 = medusa.components.Recording.load(file_1)
data = recording.eeg.signal
fss = recording.eeg.fs
window_length = 8000
window_length = window_length/1000*fss
epochs = medusa.get_epochs(data, window_length)
scales = [1,3]
mlzc = multiscale_lempelziv_complexity(epochs, scales)
print(np.shape(mlzc))
print(mlzc[:, 1, :])
hola = 1