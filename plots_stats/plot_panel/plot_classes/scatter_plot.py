# plots_stats/plot_panel/plot_classes/scatter_plot.py

import numpy as np
import scipy.io
from typing import Dict, List
from .base_plot import BasePlot


class ScatterPlot(BasePlot):
    """
    Scatter plot:
    X = selected secondary parameter
    Y = tab parameter
    One point per file, colored by group
    """

    def __init__(self, ax, plot_params=None, tabs_widget=None):
        super().__init__(ax, plot_params, tabs_widget)
        self._points = {}  # group -> (x_vals, y_vals)
        self.tabs_widget = tabs_widget

    def load_data(self, filtered_files_y: Dict[str, List[str]], filtered_files_x: Dict[str, List[str]],
        selected_channels: List[int]):

        self._points.clear()
        for group, files_y in filtered_files_y.items():
            files_x = filtered_files_x.get(group, [])
            if not files_x:
                continue

            x_vals = []
            y_vals = []

            files_x_map = {self._base_name(f): f for f in files_x}

            for fy in files_y:
                key = self._base_name(fy)
                fx = files_x_map.get(key)
                if fx is None:
                    continue
                y = self._load_scalar(fy, selected_channels)
                x = self._load_scalar(fx, selected_channels)
                if x is None or y is None:
                    continue
                x_vals.append(x)
                y_vals.append(y)

            if x_vals and y_vals:
                self._points[group] = (np.array(x_vals), np.array(y_vals))

    def draw(self, colors=None):
        self.clear()

        if not self._points:
            print("[WARN] No scatter data to plot.")
            return

        size = self.plot_params.get("marker_size", 60)
        alpha = self.plot_params.get("alpha", 0.8)

        for group, (x, y) in self._points.items():
            color = colors.get(group) if isinstance(colors, dict) else None
            self.ax.scatter(x, y, s=size, alpha=alpha, label=group, color=color)

        if self.plot_params.get("show_line", False):
            all_x = np.concatenate([v[0] for v in self._points.values()])
            all_y = np.concatenate([v[1] for v in self._points.values()])

            if len(all_x) > 1:
                coeffs = np.polyfit(all_x, all_y, 1)
                x_line = np.linspace(all_x.min(), all_x.max(), 100)
                y_line = coeffs[0] * x_line + coeffs[1]
                self.ax.plot(x_line, y_line, linestyle="-", linewidth=1, color='red')

        self.ax.legend(frameon=False)

        self.safe_set_lim("set_xlim", self.plot_params.get("xlim"))
        self.safe_set_lim("set_ylim", self.plot_params.get("ylim"))
        self.apply_grid_and_spines(axis="y")
        self.save_limits()

    # ---------- helpers ----------

    def _load_scalar(self, filepath, selected_channels):
        try:
            mat = scipy.io.loadmat(filepath, squeeze_me=True, struct_as_record=False)
        except Exception:
            return None

        for key in ("param", "vector", "values", "valores"):
            if key in mat:
                data = np.asarray(mat[key]).squeeze()
                break
        else:
            return None

        data = self.normalize_data(data, selected_channels)
        if data is None:
            return None

        if selected_channels:
            try:
                data = data[selected_channels]
            except Exception:
                return None

        return float(np.mean(data))

    def _base_name(self, filepath):
        import re, os
        name = os.path.basename(filepath)
        name = re.sub(r"_param-[^_]+", "", name) # remove param info
        name = re.sub(r"_band-[^_]+", "", name) # remove band info
        return name
