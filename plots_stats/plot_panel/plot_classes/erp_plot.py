import numpy as np
import scipy.io
from typing import Dict, List
from .base_plot import BasePlot


class ERPPlot(BasePlot):
    """
    Plot de Event-Related Potentials (ERP).

    Soporta datos con forma:
    - (epochs, times, channels)
    - (times, channels)

    Para cada grupo:
    - promedia épocas (si existen)
    - promedia canales seleccionados
    - promedia entre archivos
    """

    def __init__(self, ax, plot_params=None):
        super().__init__(ax, plot_params)
        self._group_erps = {}

    def load_data(self, filtered_files: Dict[str, List[str]], selected_channels: List[int]):
        self._group_erps.clear()

        for group_name, file_list in filtered_files.items():
            group_signals = []

            for filepath in file_list:
                try:
                    mat = scipy.io.loadmat(filepath, squeeze_me=True, struct_as_record=False)
                except Exception as e:
                    print(f"[ERROR] Cannot load .mat file {filepath}: {e}")
                    continue

                data = None
                for key in (["epochs"]):
                    if key in mat:
                        data = np.asarray(mat[key])
                        break

                if data is None:
                    print(f"[WARN] No ERP data found in {filepath}")
                    continue

                data = np.asarray(data)
                data = self.normalize_data(data)  # aquí se aplican todos los casos 1D, 2D, 3D
                if data.ndim != 2:
                    print(f"[WARN] Unsupported ERP shape {data.shape} in {filepath}")
                    continue

                times, n_channels = data.shape
                valid_channels = [ch for ch in selected_channels if 0 <= ch < n_channels]
                if not valid_channels:
                    valid_channels = [0]

                signal = np.mean(data[:, valid_channels], axis=1)
                group_signals.append(signal)

            if group_signals:
                min_len = min(s.shape[0] for s in group_signals)
                aligned = np.array([s[:min_len] for s in group_signals])
                self._group_erps[group_name] = np.mean(aligned, axis=0)

    def draw(self, colors=None):
        self.clear()

        if not self._group_erps:
            print("[WARN] No ERP data to plot.")
            return

        line_width = self.plot_params.get("line_width", 2)
        line_style = self.plot_params.get("line_style", "solid")

        for group_name, erp in self._group_erps.items():
            color = colors.get(group_name) if isinstance(colors, dict) else None
            t = np.arange(erp.size)

            self.ax.plot(
                t,
                erp,
                label=group_name,
                linewidth=line_width,
                linestyle=line_style,
                color=color
            )

        self.ax.legend(frameon=False)

        self.safe_set_lim("set_xlim", self.plot_params.get("xlim"))
        self.safe_set_lim("set_ylim", self.plot_params.get("ylim"))

        self.apply_grid_and_spines(axis="both")
        self.save_limits()
