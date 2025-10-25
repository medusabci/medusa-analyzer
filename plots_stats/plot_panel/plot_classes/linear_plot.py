import numpy as np
import scipy.io
from typing import Any, Dict, List
from .base_plot import BasePlot


class LinearPlot(BasePlot):
    """
    Plot class for simple 1x32 vector data.
    For each group, loads all .mat files (each containing a 1x32 vector),
    averages across selected channels and files, and plots the result.
    """

    def __init__(self, ax, plot_params=None):
        super().__init__(ax, plot_params)
        self._group_means = {}

    def load_data(
        self,
        filtered_files: Dict[str, List[str]],
        selected_channels: List[int],
    ):
        """
        Load and average data from .mat files for each group.

        Args:
            filtered_files: dict {group_name: [filepaths]}
            selected_channels: list of int channel indices
        """
        self._group_means.clear()

        for group_name, file_list in filtered_files.items():
            group_values = []

            for filepath in file_list:
                try:
                    mat = scipy.io.loadmat(filepath, squeeze_me=True, struct_as_record=False)
                except Exception as e:
                    print(f"[ERROR] Cannot load .mat file {filepath}: {e}")
                    continue

                # Buscar el vector de datos (intentamos varias claves posibles)
                data = None
                for key in ("data", "vector", "values", "valores"):
                    if key in mat:
                        data = np.asarray(mat[key]).squeeze()
                        break

                if data is None:
                    # Si el archivo tiene solo una variable, cogemos la primera que parezca un vector
                    for key, val in mat.items():
                        if isinstance(val, np.ndarray) and val.ndim == 1 and val.size == 32:
                            data = val
                            break

                if data is None:
                    print(f"[WARN] No valid 1x32 vector found in {filepath}")
                    continue

                # Validar tamaño
                if data.size != 32:
                    print(f"[WARN] Unexpected vector size ({data.size}) in {filepath}")
                    continue

                # Validar canales seleccionados
                valid_channels = [ch for ch in selected_channels if 0 <= ch < data.size]
                if not valid_channels:
                    valid_channels = [0]  # por defecto canal 0

                # Promedio entre canales seleccionados
                mean_value = np.mean(data[valid_channels])
                group_values.append(mean_value)

            if group_values:
                self._group_means[group_name] = np.mean(group_values)

    def draw(self):
        """
        Draw a simple line connecting each group's average value.
        """
        self.clear()

        if not self._group_means:
            print("[WARN] No LinearPlot data to plot.")
            return

        group_names = list(self._group_means.keys())
        y_values = [self._group_means[g] for g in group_names]
        x_values = np.arange(len(group_names))

        self.ax.plot(x_values, y_values, color = self.plot_params["line_color"], marker="o", linestyle="-", linewidth=2, markersize=8)
        self.ax.set_xticks(x_values)
        self.ax.set_xticklabels(group_names, fontsize=7, rotation=45, ha="right")

        self.ax.set_xlabel(self.plot_params.get("x_label", "Groups"))
        self.ax.set_ylabel(self.plot_params.get("y_label", "Mean Value"))
        title = self.plot_params.get("title", "")
        xlim = self.plot_params.get("xlim", None)
        ylim = self.plot_params.get("ylim", None)
        if title:
            self.ax.set_title(title)
        if xlim is not None:
            self.ax.set_xlim(xlim)
        if ylim is not None:
            self.ax.set_ylim(ylim)

        self.ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.6)
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.relim()
        self.ax.autoscale_view()
