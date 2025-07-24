import os
import numpy as np
import scipy.io as sio
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import medusa.components
from medusa.plots import head_plots

# === CONFIGURACIÓN GENERAL ===
sns.set(style='whitegrid', context='talk')
base_path = r'D:\Proyectos\medusa-analyzer\data\Signal_parameters'
base_path_channels = r'D:\Proyectos\medusa-analyzer\data\Preprocessed_signals'
subjects = [f"R{i}" for i in range(1, 6)]
conditions = {'Eyes Open': 'eyes-open', 'Eyes Closed': 'eyes-closed'}
percentile_th = 80
frequencies = np.linspace(0, 250, 1001)
freq_mask = frequencies <= 60

# === FUNCIONES GENÉRICAS ===
def load_mat_param(file, key):
    path = os.path.join(base_path, file)
    param = sio.loadmat(path, squeeze_me=True)['parameters'][key]
    return np.asarray(param.item() if param.dtype == 'O' else param)

def average_psd(files):
    return np.nanmean([np.mean(load_mat_param(f, 'psd'), axis=0) for f in files], axis=0).mean(axis=-1)

def average_metric(files, key, shape_check=None):
    data = []
    for f in files:
        val = load_mat_param(f, key).astype(np.float64).squeeze()
        if shape_check and val.shape != shape_check:
            raise ValueError(f"{f} tiene forma {val.shape}, se esperaba {shape_check}")
        data.append(val)
    return np.nanmean(np.stack(data), axis=0)

def get_files(suffix):
    return [f"{s}.rec_parameters_{cond}_{suffix}.mat" for s in subjects for cond in conditions.values()]

# === CARGA DE CANALES ===
ch_path = os.path.join(base_path_channels, f"{subjects[0]}.rec_preprocessing_broadband.mat")
channel_set = medusa.components.Recording.load(ch_path).eeg.channel_set

# === PSD COMPARATIVO ===
files_open = [f"{s}.rec_parameters_eyes-open_broadband.mat" for s in subjects]
files_closed = [f"{s}.rec_parameters_eyes-closed_broadband.mat" for s in subjects]
psd_open = average_psd(files_open)[freq_mask]
psd_closed = average_psd(files_closed)[freq_mask]
freqs_plot = frequencies[freq_mask]

plt.figure(figsize=(12, 7))
plt.plot(freqs_plot, psd_closed, label='Eyes Closed', color='navy', lw=2.5)
plt.plot(freqs_plot, psd_open, label='Eyes Open', color='darkred', lw=2.5)
for a, b, name, col in [(0,4,'Delta','#a6cee3'),(4,8,'Theta','#b2df8a'),(8,13,'Alpha','#fb9a99'),
                        (13,20,'Beta1','#fdbf6f'),(20,30,'Beta2','#ff7f00'),(30,60,'Gamma','#cab2d6')]:
    plt.axvspan(a, b, color=col, alpha=0.25)
    plt.text((a+b)/2, plt.ylim()[1], name, ha='center', va='top', fontsize=16, weight='bold')
plt.xlabel('Frequency (Hz)', fontsize=18); plt.ylabel('Power spectral density (µV²/Hz)', fontsize=18)
plt.xlim(0, 60); plt.ylim(0, 9); plt.legend(fontsize=16); plt.grid(True, ls='--', alpha=0.4)
plt.tight_layout(); plt.grid(False); plt.savefig('psd_comparativo_con_bandas.png', dpi=300); plt.show()
# QUITA EL GRID DE CADA UNA

# === TOPOPLOT RELATIVE POWER (ALPHA) ===
alpha_open = average_metric(files_open, 'relative_power_Alpha', (32,))
alpha_closed = average_metric(files_closed, 'relative_power_Alpha', (32,))
vmin, vmax = min(alpha_open.min(), alpha_closed.min()), max(alpha_open.max(), alpha_closed.max())

fig, axs = plt.subplots(1, 2, figsize=(10, 5))
for ax, data, title in zip(axs, [alpha_closed, alpha_open], ['Eyes Closed', 'Eyes Open']):
    topo = head_plots.TopographicPlot(ax, channel_set, clim=(vmin, vmax), cmap='YlOrRd',
                                       plot_channel_labels=False, plot_channel_points=True,
                                       interp_points=300, interp_contour_width=0.6)
    ax.set_title(title, fontsize=18); ax.grid(False); topo.update(data)
plt.subplots_adjust(left=0.06, right=0.86, top=0.85, bottom=0.1, wspace=0.2)
sm = plt.cm.ScalarMappable(cmap='YlOrRd', norm=plt.Normalize(vmin, vmax))
cbar = plt.colorbar(sm, cax=fig.add_axes([0.88, 0.15, 0.02, 0.7]))
# INCLUIR EN LA PARTE DE ARRIBA DE LA COLOR BAR LAS UNIDADES DE LA POTENCIA RELATIVA
plt.savefig("topoplot_relative_alpha.png", dpi=300); plt.show()

# === TOPOPLOT AEC ===
aec_open = average_metric(files_open, 'aec', (32, 32))
aec_closed = average_metric(files_closed, 'aec', (32, 32))
masked = np.concatenate([aec_open[aec_open != 1], aec_closed[aec_closed != 1]])
vmin, vmax = masked.min(), masked.max()

fig, axs = plt.subplots(1, 2, figsize=(10, 5))
for ax, data, title in zip(axs, [aec_closed, aec_open], ['Eyes Closed', 'Eyes Open']):
    conn = head_plots.ConnectivityPlot(ax, channel_set, clim=(vmin, vmax),
                                       percentile_th=percentile_th, cmap='inferno_r')
    ax.set_title(title, fontsize=18); ax.grid(False); conn.update(data)
plt.subplots_adjust(left=0.06, right=0.86, top=0.85, bottom=0.1, wspace=0.2)
sm = plt.cm.ScalarMappable(cmap='inferno_r', norm=plt.Normalize(vmin, vmax))
plt.colorbar(sm, cax=fig.add_axes([0.88, 0.15, 0.02, 0.7]))
# INCLUIR EN LA PARTE DE ARRIBA DE LA COLORBAR LAS UNIDADES DE LA AEC
plt.savefig("topoplot_aec_80.png", dpi=300);
plt.show()

# A PARTE, QUIERO QUE ME CREES UNA FIGURA GRANDE, CON TRES SUBPLOTS. EL PRIMER SUBPLOT CON LA PSD,
# EL SEGUNDO SUBPLOT CON LOS TOPOS DE LA POTENCIA RELATIVA Y EL TERCERO CON LOS TOPOS DE CONECTIVIDAD. GUARDALO
# CON EL NOMBRE DE FIGURA FINAL Y CON 300 DPI