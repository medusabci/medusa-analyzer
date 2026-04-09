import numpy as np
import scipy.io
from typing import Dict, List
from .base_plot import BasePlot


class PSDPlot(BasePlot):
    """
    Plot class for Power Spectral Density (PSD) data.
    Handles loading, averaging, and plotting PSD curves for multiple groups.
    """

    def __init__(self, ax, plot_params=None,tabs_widget=None):
        super().__init__(ax, plot_params, tabs_widget)
        self._freqs = None
        self._psd_data = {}
        self.tabs_widget = tabs_widget

    def load_data(self, filtered_files: Dict[str, List[str]], selected_channels: List[int]):
        self._psd_data.clear()
        self._freqs = None

        groups = []

        for group_name, file_list in filtered_files.items():
            subject_psds = []
            freqs_ref = None

            for filepath in file_list:
                try:
                    mat = scipy.io.loadmat(filepath, squeeze_me=True, struct_as_record=False)
                except Exception as e:
                    print(f"[ERROR] Cannot load .mat file {filepath}: {e}")
                    continue

                psd_struct = None
                for key in ("param", "psd", "psd_struct", "PSD", "PSD_struct"):
                    if key in mat:
                        psd_struct = mat[key]
                        break

                if psd_struct is None:
                    print(f"[WARN] No PSD struct found in {filepath}; skipping.")
                    continue

                freqs, values = self._extract_psd_fields(psd_struct)
                if freqs is None or values is None:
                    print(f"[WARN] Missing PSD fields in {filepath}; skipping.")
                    continue

                freqs = np.asarray(freqs).squeeze()
                values = np.asarray(values)

                values = self.normalize_data_psd(values)
                if values.shape[1] == freqs.size:
                    values = values.T

                max_idx = values.shape[1] - 1
                valid_channels = [ch for ch in selected_channels if 0 <= ch <= max_idx] or [0]
                mean_psd = np.mean(values[:, valid_channels], axis=1)

                if freqs_ref is None:
                    freqs_ref = freqs

                if not np.array_equal(freqs, freqs_ref):
                    try:
                        mean_psd = np.interp(freqs_ref, freqs, mean_psd)
                    except Exception as e:
                        print(f"[WARN] Interpolation failed for {filepath}: {e}")
                        continue

                subject_id = self.extract_subject_id(filepath)
                subject_psds.append((subject_id, mean_psd))

            if not subject_psds:
                continue

            subject_matrix = self.aggregate_subject_data(subject_psds)
            if subject_matrix.size == 0:
                continue

            group_mean = np.mean(subject_matrix, axis=0)
            group_std = np.std(subject_matrix, axis=0)
            n_subjects = subject_matrix.shape[0]
            
            groups.append((group_name, freqs_ref, group_mean, subject_matrix, group_std, n_subjects))

        if groups:
            self._freqs = groups[0][1]
            # Ahora guardamos un dict con mean, std, n
            self._psd_data = {g[0]: {"mean": g[2], "std": g[4], "n": g[5]} for g in groups}
            self._psd_data_stats = {g[0]: g[3] for g in groups}

        current_tab = next((tab for tab in self.tabs_widget.tab_widgets if tab._plot is self), None)
        if not hasattr(current_tab, 'statistics'):
            self.prepare_stats_data(current_tab)

    def _extract_psd_fields(self, psd_struct):
        freqs, values = None, None
        try:
            if isinstance(psd_struct, dict):
                freqs = psd_struct.get("freqs")
                values = psd_struct.get("values")
            else:
                freqs = getattr(psd_struct, "freqs", None)
                values = getattr(psd_struct, "values", None)
        except Exception:
            pass
        return freqs, values

    def draw(self, colors: Dict[str, str] = None):
        self.clear()

        if not self._psd_data or self._freqs is None:
            print("[WARN] No PSD data to plot.")
            return

        line_width = self.plot_params.get("line_width", 2)
        linestyle_map = {"solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-." }
        line_style = linestyle_map.get(self.plot_params.get("line_style", "-"), "-")
        plot_error = self.plot_params.get("plot_error", False)

        all_values = []

        for group_name, data in self._psd_data.items():
            color = colors.get(group_name) if isinstance(colors, dict) else None
            
            mean_psd = data["mean"]
            std_psd = data["std"]
            n_subjects = data["n"]

            self.ax.plot(
                self._freqs,
                mean_psd,
                label=group_name,
                color=color,
                linestyle=line_style,
                linewidth=line_width,
                alpha=0.9
            )
            
            if plot_error and n_subjects > 1:
                ci = 1.96 * (std_psd / np.sqrt(n_subjects))
                self.ax.fill_between(
                    self._freqs, 
                    mean_psd - ci, 
                    mean_psd + ci, 
                    color=color, 
                    alpha=0.25
                )
                
            all_values.append(mean_psd)

        bands = [
            (0, 4, "Delta", "#a6cee3"),
            (4, 8, "Theta", "#b2df8a"),
            (8, 13, "Alpha", "#fb9a99"),
            (13, 20, "Beta 1", "#fdbf6f"),
            (20, 30, "Beta 2", "#ff7f00"),
            (30, None, "Gamma", "#cab2d6"),
        ]

        x_max = float(np.nanmax(self._freqs))
        for start, end, _, color in bands:
            self.ax.axvspan(
                start,
                end if end is not None else x_max,
                color=color,
                alpha=0.2,
                zorder=0,
                linewidth=0
            )

        # Get whether to show the stats bars
        stats_checkbox = bool(self.plot_params.get("plot_stats", False))

        if stats_checkbox:
            current_tab = next((tab for tab in self.tabs_widget.tab_widgets if tab._plot is self), None)

            # Run the statistical analysis if it has not been done yet
            if not 'statistical_results' in current_tab.statistics.keys():
                self.tabs_widget.controller.stats_report(current_tab, is_continuous=True)

            p_vals = current_tab.statistics['statistical_results']
            # p_vals = np.random.uniform(low=0.0, high=0.1, size=len(self._freqs))
            # Shading for p-values
            self.ax.fill_between(
                self._freqs,
                0, 1,
                where=(p_vals < 0.05),
                facecolor="gray",
                edgecolor="black",
                linewidth=1.5,
                alpha=0.1,
                transform=self.ax.get_xaxis_transform(),
                zorder=0,
                label="p < 0.05"
            )

        # Límites y estilo desde BasePlot
        self.safe_set_lim("set_xlim", self.plot_params.get("xlim"))
        self.safe_set_lim("set_ylim", self.plot_params.get("ylim"))
        self.apply_grid_and_spines(axis="both")
        self.ax.legend(frameon=False)
        self.save_limits()

    def prepare_stats_data(self, current_tab):
        groups = []
        data = []
        for group_name, values in self._psd_data_stats.items():
            data.extend(values)
            groups.extend([group_name] * values.shape[0])

        current_tab.statistics = {}
        current_tab.statistics['data'] = data
        current_tab.statistics['groups'] = groups
