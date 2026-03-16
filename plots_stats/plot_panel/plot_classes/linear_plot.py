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

    def __init__(self, ax, plot_params=None, main_module=None):
        super().__init__(ax, plot_params, main_module=main_module)
        self._group_stats = {}

        self._mode = None  # "vector" | "time_series"
        self._group_series = {}

    def load_data(self, filtered_files: Dict[str, List[str]], selected_channels: List[int]):
        """
        Load and average data from .mat files for each group.

        Args:
            filtered_files: dict {group_name: [filepaths]}
            selected_channels: list of int channel indices
        """
        self._group_stats.clear()
        self._group_series.clear()
        self._mode = None

        for group_name, file_list in filtered_files.items():
            group_values = []
            group_series = []

            for filepath in file_list:
                try:
                    mat = scipy.io.loadmat(filepath, squeeze_me=True, struct_as_record=False)
                except Exception as e:
                    print(f"[ERROR] Cannot load .mat file {filepath}: {e}")
                    continue

                data = None
                for key in ("param", "vector", "values", "valores"):
                    if key in mat:
                        data = np.asarray(mat[key]).squeeze()
                        break

                if data is None:
                    for key, val in mat.items():
                        if isinstance(val, np.ndarray) and val.ndim == 1:
                            data = val
                            break

                if data is None:
                    print(f"[WARN] No valid data found in {filepath}")
                    continue

                data = np.asarray(data)
                if data.ndim == 2:
                    self._mode = "time_series"

                    max_idx = data.shape[1] - 1
                    valid_channels = [ch for ch in selected_channels if 0 <= ch <= max_idx]
                    if not valid_channels:
                        valid_channels = [0]

                    # average over channels → signal over time
                    signal = np.mean(data[:, valid_channels], axis=1)
                    group_series.append(signal)

                else:
                    print(f"[WARN] Unsupported data shape {data.shape} in {filepath}")
                    continue

            if self._mode == "vector" and group_values:
                self._group_stats[group_name] = {
                    "mean": np.mean(group_values),
                    "std": np.std(group_values)
                }

            if self._mode == "time_series" and group_series:
                min_len = min(s.shape[0] for s in group_series)
                truncated_series = np.array([s[:min_len] for s in group_series])
                self._group_series[group_name] = np.mean(truncated_series, axis=0)


    def draw(self, colors=None):
        self.clear()

        if self._mode == "time_series":
            if not self._group_series:
                print("[WARN] No time-series data to plot.")
                return

            line_width = self.plot_params.get("line_width", 2)

            for group_name, signal in self._group_series.items():
                color = colors.get(group_name) if isinstance(colors, dict) else None

                t = np.arange(signal.size)  # epochs as time
                self.ax.plot(t, signal, label=group_name, linewidth=line_width, color=color)

            self.ax.set_xlabel("Time (epochs)")
            self.ax.legend(frameon=False)
        else:
            print("[WARN] No LinearPlot data to plot.")

        self.safe_set_lim("set_xlim", self.plot_params.get("xlim"))
        self.safe_set_lim("set_ylim", self.plot_params.get("ylim"))
        self.apply_grid_and_spines(axis="y")
        self.save_limits()

