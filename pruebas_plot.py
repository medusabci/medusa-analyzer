import os
import scipy.io
import scipy.signal
import matplotlib.pyplot as plt
import numpy as np
import medusa


# Ruta donde están los archivos
directorio = r'D:\Proyectos\medusa-analyzer\hola_band\Preprocessed signals'

# Lista de nombres de archivo
archivos = [
    'R0.rec_preprocessing_delta.mat',
    'R0.rec_preprocessing_theta.mat',
    'R0.rec_preprocessing_alpha.mat',
    'R0.rec_preprocessing_beta.mat',
    'R0.rec_preprocessing_gamma.mat',
    'R0.rec_preprocessing_broadband.mat'
]

# Parámetros PSD
fs = 256
nperseg = 256
noverlap = 128
nfft = 512

for nombre_archivo in archivos:
    path_archivo = os.path.join(directorio, nombre_archivo)

    if not os.path.exists(path_archivo):
        print(f'Archivo no encontrado: {path_archivo}')
        continue

    # Cargar .mat
    mat = scipy.io.loadmat(path_archivo, struct_as_record=False, squeeze_me=True)
    signal = registro = mat['eeg'].signal  # Debe ser (6544 x 4)
    if signal.ndim != 2 or signal.shape[1] != 4:
        print(f'Formato inesperado en signal en {nombre_archivo}')
        continue

    # Graficar
    fig, axs = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle(nombre_archivo)

    for canal in range(4):
        x = signal[:, canal]
        f, Pxx = scipy.signal.welch(x, fs=fs, nperseg=nperseg, noverlap=noverlap, nfft=nfft)

        ax = axs[canal // 2, canal % 2]
        ax.plot(f, 10 * np.log10(Pxx))
        ax.set_title(f'Canal {canal + 1}')
        ax.set_xlabel('Frecuencia (Hz)')
        ax.set_ylabel('PSD (dB/Hz)')
        ax.grid(True)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()
