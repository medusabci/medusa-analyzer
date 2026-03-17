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
            per_file_psds = []
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
                per_file_psds.append((freqs, mean_psd))

                if freqs_ref is None:
                    freqs_ref = freqs

            if not per_file_psds:
                continue

            freqs_common = freqs_ref
            interpolated = []

            for fvec, pvec in per_file_psds:
                if not np.array_equal(fvec, freqs_common):
                    try:
                        pvec = np.interp(freqs_common, fvec, pvec)
                    except Exception as e:
                        print(f"[WARN] Interpolation failed for {group_name}: {e}")
                        continue
                interpolated.append(pvec)

            if interpolated:
                group_mean = np.mean(np.vstack(interpolated), axis=0)
                groups.append((group_name, freqs_common, group_mean))

        if groups:
            self._freqs = groups[0][1]
            self._psd_data = {g[0]: g[2] for g in groups}

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

        all_values = []

        for group_name, pxx in self._psd_data.items():
            color = colors.get(group_name) if isinstance(colors, dict) else None

            self.ax.plot(
                self._freqs,
                pxx,
                label=group_name,
                color=color,
                linestyle=line_style,
                linewidth=line_width,
                alpha=0.9
            )
            all_values.append(pxx)

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
                zorder=0
            )

        # Límites y estilo desde BasePlot
        self.safe_set_lim("set_xlim", self.plot_params.get("xlim"))
        self.safe_set_lim("set_ylim", self.plot_params.get("ylim"))
        self.apply_grid_and_spines(axis="both")
        self.ax.legend(frameon=False)
        self.save_limits()
