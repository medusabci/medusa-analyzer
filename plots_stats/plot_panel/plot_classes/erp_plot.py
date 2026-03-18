import numpy as np
import scipy.io
from typing import Dict, List
from .base_plot import BasePlot


class ERPPlot(BasePlot):
    """
    Plot of Event-Related Potentials (ERP).

    For each group:
    - Average epochs (if exists)
    - Average selected channels
    - Average files
    """

    def __init__(self, ax, plot_params=None, tabs_widget=None):
        super().__init__(ax, plot_params, tabs_widget)
        self._group_erps = {}
        self._time_vector = None
        self.tabs_widget = tabs_widget

    def load_data(self, filtered_files: Dict[str, List[str]], selected_channels: List[int]):
        self._group_erps.clear()
        self._time_vector = None

        # Loop to iterate through groups
        for group_name, file_list in filtered_files.items():
            subject_signals = []

            # Loop to iterate through all files for each group
            for filepath in file_list:
                try:
                    mat = scipy.io.loadmat(filepath, squeeze_me=True, struct_as_record=False)
                except Exception as e:
                    print(f"[ERROR] Cannot load .mat file {filepath}: {e}")
                    continue

                data = None
                if "epochs" in mat:
                    data = np.asarray(mat["epochs"])
                if data is None:
                    print(f"[WARN] No ERP data found in {filepath}")
                    continue

                data = self.normalize_data(data)
                if data.ndim != 2:
                    print(f"[WARN] Unsupported ERP shape {data.shape} in {filepath}")
                    continue

                times, n_channels = data.shape
                valid_channels = [ch for ch in selected_channels if 0 <= ch < n_channels]
                if not valid_channels:
                    valid_channels = [0]

                signal = np.mean(data[:, valid_channels], axis=1)
                subject_id = self.extract_subject_id(filepath)
                subject_signals.append((subject_id, signal))

            if subject_signals:
                signals = self.aggregate_subject_data(subject_signals)
                if signals.size == 0:
                    continue
                mean_signal = np.mean(signals, axis=0)
                std_signal = np.std(signals, axis=0)
                n = signals.shape[0]

                self._group_erps[group_name] = {
                    "mean": mean_signal,
                    "std": std_signal,
                    "n": n,
                    "all": signals
                }
            if self._time_vector is None:
                window = self.plot_params.get("_time_window", None)
                if window is not None:
                    start, end = window
                    self._time_vector = np.linspace(start, end, signals.shape[1])

        if not hasattr(self.tabs_widget, 'statistics'):
            self.prepare_stats_data(self.tabs_widget)

    def draw(self, colors=None):
        self.clear()

        if not self._group_erps:
            print("[WARN] No ERP data to plot.")
            return

        line_width = self.plot_params.get("line_width", 2)
        line_style = self.plot_params.get("line_style", "solid")

        plot_error = self.plot_params.get("plot_error", False)
        for group_name, data in self._group_erps.items():
            mean = data["mean"]
            std = data["std"]
            n = data["n"]
            color = colors.get(group_name) if isinstance(colors, dict) else None
            if self._time_vector is not None:
                t = self._time_vector
            else:
                t = np.arange(mean.size)

            self.ax.plot(t, mean, label=group_name, linewidth=line_width, linestyle=line_style,
                color=color)
            if plot_error and n > 1:
                ci = 1.96 * (std / np.sqrt(n))
                self.ax.fill_between(t, mean - ci, mean + ci, color=color, alpha=0.25)

        self.ax.legend(frameon=False)

        # Vertical zero-line
        if self._time_vector is not None:
            if self._time_vector[0] <= 0 <= self._time_vector[-1]:
                self.ax.axvline(0, color="gray", linestyle="--", linewidth=1, alpha=0.8)

        self.safe_set_lim("set_xlim", self.plot_params.get("xlim"))
        self.safe_set_lim("set_ylim", self.plot_params.get("ylim"))

        self.apply_grid_and_spines(axis="both")
        self.save_limits()


    def prepare_stats_data(self, current_tab):
        groups = []
        data = []
        for group_name, values in self._group_erps.items():
            data.extend(values['all'])
            groups.extend([group_name] * values['all'].shape[0])

        current_tab.statistics = {}
        current_tab.statistics['data'] = data
        current_tab.statistics['groups'] = groups

        # current_tab.controller.stats_report(current_tab, skip_report=True, is_continuous=True)