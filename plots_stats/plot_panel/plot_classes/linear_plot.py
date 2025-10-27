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
                    valid_channels = [0]  # por defecto canal 0

                # Average of selected channels
                mean_value = np.mean(data[valid_channels])
                group_values.append(mean_value)

            if group_values:
                self._group_stats[group_name] = {
                    "mean": np.mean(group_values),
                    "std": np.std(group_values)
                }

    def draw(self, colors = None):
        """
        Draw a simple line connecting each group's average value.
        """
        self.clear()

        if not self._group_stats:
            print("[WARN] No LinearPlot data to plot.")
            return

        group_names = list(self._group_stats.keys())
        y_mean = np.array([self._group_stats[g]["mean"] for g in group_names])
        y_std = np.array([self._group_stats[g]["std"] for g in group_names])
        x_values = np.arange(len(group_names))

        if colors and len(colors) >= len(group_names):
            for i, color in enumerate(colors[:len(group_names)]):
                self.ax.axvspan(i - 0.5, i + 0.5, color=color, alpha=0.15, zorder=0)
        elif colors:
            print(f"[WARN] Number of colors ({len(colors)}) != number of groups ({len(group_names)})")

        self.ax.plot(x_values, y_mean, color = self.plot_params["line_color"], marker="o", linestyle="-",
                     linewidth=2, markersize=8, label = "Mean")
        plot_std = str(self.plot_params.get("plot_std", "True")).lower() in ("1", "true", "yes")
        if plot_std:
            self.ax.fill_between(x_values, y_mean - y_std, y_mean + y_std, color = self.plot_params["line_color"],
                                 alpha = 0.15, label = "±STD")


        self.ax.set_xticks(x_values)
        self.ax.set_xticklabels(group_names, fontsize=7, rotation=45, ha="right")

        self.ax.set_xlabel(self.plot_params.get("x_label", "Groups"))
        self.ax.set_ylabel(self.plot_params.get("y_label", "Mean Value"))
        title = self.plot_params.get("title", "")
        if title:
            self.ax.set_title(title)

        self._safe_set_lim(self.ax, "set_ylim", self.plot_params.get("ylim", None))

        self.ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.6)
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.relim()
        self.ax.autoscale_view()

    def _safe_set_lim(self, ax, method, lim):
        """Utility to safely set axis limits."""
        if not isinstance(lim, (list, tuple)) or len(lim) != 2:
            return  # ignore invalid
        lo, hi = lim
        if lo is None and hi is None:
            return
        try:
            ax_method = getattr(ax, method)
            current_lo, current_hi = ax_method()
            new_lo = lo if lo is not None else current_lo
            new_hi = hi if hi is not None else current_hi
            ax_method([new_lo, new_hi])
        except Exception as e:
            print(f"[WARN] Could not apply {method}: {e}")
            pass
