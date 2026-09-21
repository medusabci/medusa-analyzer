from __future__ import annotations

import numpy as np

from .base_plot import BasePlot
from .epoch_data import PreparedEpochData


class EpochAveragePlot(BasePlot):
    """Plot aligned epoch averages for one or more groups."""

    def __init__(self, ax, plot_params=None, tabs_widget=None):
        super().__init__(ax, plot_params, tabs_widget)
        self._group_epochs: dict[str, dict[str, np.ndarray | int]] = {}
        self._time_vector: np.ndarray | None = None

    def load_data(self, *args, **kwargs) -> None:
        raise NotImplementedError("EpochAveragePlot expects prepared epoch data.")

    def load_prepared_data(self, prepared_data: PreparedEpochData) -> None:
        self._group_epochs.clear()
        self._time_vector = None

        reference_times = prepared_data.times
        if reference_times is not None:
            self._time_vector = np.asarray(reference_times, dtype=float).squeeze()

        for group in prepared_data.groups:
            signals = []
            for observation in group.observations:
                signal = np.asarray(observation.values, dtype=float).squeeze()
                times = np.asarray(observation.times, dtype=float).squeeze()
                if signal.ndim != 1 or times.ndim != 1 or signal.size == 0 or times.size == 0:
                    continue
                if signal.size != times.size:
                    min_len = min(signal.size, times.size)
                    signal = signal[:min_len]
                    times = times[:min_len]
                if self._time_vector is None:
                    self._time_vector = times
                elif times.size != self._time_vector.size or not np.allclose(times, self._time_vector):
                    signal = np.interp(self._time_vector, times, signal)
                signals.append(signal)

            if not signals:
                continue

            matrix = np.stack(signals)
            self._group_epochs[group.name] = {
                "mean": np.nanmean(matrix, axis=0),
                "std": np.nanstd(matrix, axis=0),
                "n": matrix.shape[0],
                "all": matrix,
            }

    def draw(self, colors: dict[str, str] | None = None) -> None:
        self.clear()

        if not self._group_epochs or self._time_vector is None:
            return

        line_width = self.plot_params.get("line_width", 2)
        linestyle_map = {"solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-."}
        line_style = linestyle_map.get(self.plot_params.get("line_style", "solid"), "-")
        plot_error = bool(self.plot_params.get("plot_error", False))

        for group_name, data in self._group_epochs.items():
            mean = np.asarray(data["mean"], dtype=float)
            std = np.asarray(data["std"], dtype=float)
            n_observations = int(data["n"])
            color = colors.get(group_name) if isinstance(colors, dict) else None
            self.ax.plot(self._time_vector, mean, label=group_name, linewidth=line_width,
                linestyle=line_style, color=color)
            if plot_error and n_observations > 1:
                ci = 1.96 * (std / np.sqrt(n_observations))
                self.ax.fill_between(self._time_vector, mean - ci, mean + ci, color=color, alpha=0.25)

        if self._time_vector[0] <= 0 <= self._time_vector[-1]:
            self.ax.axvline(0, color="gray", linestyle="--", linewidth=1, alpha=0.8)

        self.ax.legend(frameon=False)
        self.safe_set_lim("set_xlim", self.plot_params.get("xlim"))
        self.safe_set_lim("set_ylim", self.plot_params.get("ylim"))
        self.apply_grid_and_spines(axis="both")
        self.save_limits()


__all__ = ["EpochAveragePlot"]
