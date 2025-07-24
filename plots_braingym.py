
# Quiero que me hagas un codigo de pycharm que cargue los archivos R1.rec_parameters_eyes-closed_broadband.mat
# y R1.rec_parameters_eyes-open_broadband.mat.
# Se trata de una struct que tiene dentro 'parameters' y dentro de parameters otras cosas.
#
# Quiero que en tomes los datos de 'norm_psd' dentro de 'parameters' que tiene forma 20x1001x32 y promedies la primera
# dimension. Despues quiero que representes en la primera fila de un plot con 5 filas, el plot de la psd de ojos cerrado
# (a la izquierda) y el plot de la psd con ojos abiertos (a la derecha)
# Despues, quiero que tomes los datos de 'median_frequency_Alpha' dentro de 'parameters', de dimension 1x32 y quiero que en la segunda fila
# de la figura (esta vez sin distinguir entre izquierda y derecha) quiero que con seaborn me representes los
# violinplots de las distribuciones en cada uno de los canales de la frecuencia mediana. El violinplot tiene que estar
# diviido a la mitad a lo largo del eje longitudinal, siendo la mitad izquierda correspondiente a los cojos cerrados
# y la mitad derecha correspondiente a los ojos abiertos. En el retso de filas por ahora no hacemos nada.

import scipy.io
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# Carga de los archivos .mat
closed_mat = scipy.io.loadmat(r'D:\Proyectos\medusa-analyzer\Braingym\Signal_parameters\R1.rec_parameters_eyes-closed_broadband.mat', squeeze_me=True)
open_mat = scipy.io.loadmat(r'D:\Proyectos\medusa-analyzer\Braingym\Signal_parameters\R1.rec_parameters_eyes-open_broadband.mat', squeeze_me=True)

# Acceso a las estructuras de parámetros
closed_params = closed_mat['parameters']
open_params = open_mat['parameters']

# Obtener y promediar norm_psd
closed_psd = closed_params['norm_psd']  # shape (20, 1001, 32)
open_psd = open_params['norm_psd']

# mean_closed_psd = np.mean(closed_psd, axis=0)  # shape (1001, 32)
# mean_open_psd = np.mean(open_psd, axis=0)

# Obtener median_frequency_Alpha
median_closed = closed_params['median_frequency_Alpha']  # shape (32,)
median_open = open_params['median_frequency_Alpha']      # shape (32,)

# Preparar figura
fig, axs = plt.subplots(5, 2, figsize=(14, 18))  # 5 filas, 2 columnas (ojos cerrados / abiertos)
fig.subplots_adjust(hspace=0.5)

# === Fila 1: PSD promedio por canal ===
# Promediar sobre canales para representar curva media
# avg_psd_closed = np.mean(mean_closed_psd, axis=1)  # (1001,)
# avg_psd_open = np.mean(mean_open_psd, axis=1)      # (1001,)
# freqs = np.linspace(0, 100, mean_closed_psd.shape[0])  # Suponiendo 0–100 Hz con 1001 puntos
#
# axs[0, 0].plot(freqs, avg_psd_closed, color='blue')
# axs[0, 0].set_title('PSD Promedio - Ojos Cerrados')
# axs[0, 0].set_xlabel('Frecuencia (Hz)')
# axs[0, 0].set_ylabel('Potencia Normalizada')
#
# axs[0, 1].plot(freqs, avg_psd_open, color='red')
# axs[0, 1].set_title('PSD Promedio - Ojos Abiertos')
# axs[0, 1].set_xlabel('Frecuencia (Hz)')
# axs[0, 1].set_ylabel('Potencia Normalizada')

# === Fila 2: Violinplot de median_frequency_Alpha por canal ===
# Crear DataFrame para seaborn
data = []
channels = [f'Ch{i+1}' for i in range(32)]

for i, ch in enumerate(channels):
    data.append({'Channel': ch, 'Frequency': median_closed[i], 'Condition': 'Closed'})
    data.append({'Channel': ch, 'Frequency': median_open[i], 'Condition': 'Open'})

df = pd.DataFrame(data)

# Dibujar violinplot dividido por condición (lado izquierdo/derecho)
sns.violinplot(
    data=df,
    x='Channel',
    y='Frequency',
    hue='Condition',
    split=True,
    ax=axs[1, 0],
    palette={'Closed': 'blue', 'Open': 'red'},
    inner='quartile'
)

axs[1, 0].set_title('Frecuencia Mediana en Banda Alpha por Canal')
axs[1, 0].set_ylabel('Frecuencia (Hz)')
axs[1, 0].set_xlabel('Canal')
axs[1, 1].axis('off')  # No usamos el subplot derecho de esta fila

# Mostrar figura
plt.tight_layout()
plt.show()
