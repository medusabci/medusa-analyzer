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
        self._group_stats = {}

    def load_data(self, filtered_files: Dict[str, List[str]], selected_channels: List[int]):
        """
        Load and average data from .mat files for each group.

        Args:
            filtered_files: dict {group_name: [filepaths]}
            selected_channels: list of int channel indices
        """
        self._group_stats.clear()

        for group_name, file_list in filtered_files.items():
            group_values = []

            for filepath in file_list:
                try:
                    mat = scipy.io.loadmat(filepath, squeeze_me=True, struct_as_record=False)
                except Exception as e:
                    print(f"[ERROR] Cannot load .mat file {filepath}: {e}")
                    continue

                data = None
                for key in ("data", "vector", "values", "valores"):
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

                # Validate channels
                valid_channels = [ch for ch in selected_channels if 0 <= ch < data.size]
                if not valid_channels:
                    valid_channels = [0]  # by default, use first channel

                # Average of selected channels
                mean_value = np.mean(data[valid_channels])
                group_values.append(mean_value)

            if group_values:
                self._group_stats[group_name] = {
                    "mean": np.mean(group_values),
                    "std": np.std(group_values)
                }

    def draw(self, colors=None):
        self.clear()

        if not self._group_stats:
            print("[WARN] No LinearPlot data to plot.")
            return

        group_names = list(self._group_stats.keys())
        x = np.arange(len(group_names))

        y_mean = np.array([self._group_stats[g]["mean"] for g in group_names])
        y_std = np.array([self._group_stats[g]["std"] for g in group_names])

        if isinstance(colors, dict):
            for i, g in enumerate(group_names):
                color = colors.get(g)
                if color:
                    self.ax.axvspan(
                        i - 0.5,
                        i + 0.5,
                        color=color,
                        alpha=0.15,
                        zorder=0
                    )

        line_color = self.plot_params.get("line_color", "#000000")
        line_width = self.plot_params.get("line_width", 2)

        linestyle_map = {
            "solid": "-",
            "dashed": "--",
            "dotted": ":",
            "dashdot": "-."
        }
        line_style = linestyle_map.get(self.plot_params.get("line_style", "-"), "-")
        self.ax.plot(
            x,
            y_mean,
            color=line_color,
            linestyle=line_style,
            linewidth=line_width,
            marker="o",
            markersize=8,
            label="Mean"
        )

        plot_std = bool(self.plot_params.get("plot_std", True))
        if plot_std:
            self.ax.fill_between(x, y_mean - y_std, y_mean + y_std, color=line_color, alpha=0.15,
                label="±STD")

        self.ax.set_xticks(x)
        self.ax.set_xticklabels(group_names, rotation=45, ha="right")
        self.safe_set_lim("set_ylim", self.plot_params.get("ylim"))
        self.apply_grid_and_spines(axis="y")
        self.save_limits()

