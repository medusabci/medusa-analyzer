import numpy as np
import scipy.io
from typing import Any, Dict, List, Tuple
from .base_plot import BasePlot


class PSDPlot(BasePlot):
    """
    Plot class for Power Spectral Density (PSD) data.
    Handles loading, averaging, and plotting PSD curves for multiple groups.
    """

    def __init__(self, ax, plot_params=None):
        super().__init__(ax, plot_params)
        self._freqs = None
        self._psd_data = {}

    def load_data(
        self,
        filtered_files: Dict[str, List[str]],
        selected_channels: List[int],
    ):
        """
        Load and preprocess PSD data from MATLAB files.

        Args:
            filtered_files: dict {group_name: [filepaths]}
            selected_channels: list of int channel indices
        """
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
                for key in ("psd", "PSD", "psd_struct"):
                    if key in mat:
                        psd_struct = mat[key]
                        break

                if psd_struct is None:
                    print(f"[WARN] No PSD struct found in {filepath}; skipping.")
                    continue

                # Extract frequency and power arrays
                freqs, values = self._extract_psd_fields(psd_struct)
                if freqs is None or values is None:
                    print(f"[WARN] Missing fields in {filepath}; skipping.")
                    continue

                freqs = np.asarray(freqs).squeeze()
                values = np.asarray(values)

                # Ensure shape consistency (freqs x channels)
                if values.ndim == 1:
                    values = values.reshape(-1, 1)
                elif values.shape[1] == freqs.size:
                    values = values.T

                # Validate selected channels
                max_idx = values.shape[1] - 1
                valid_channels = [ch for ch in selected_channels if 0 <= ch <= max_idx] or [0]

                selected_values = values[:, valid_channels]
                mean_psd = np.mean(selected_values, axis=1)
                per_file_psds.append((freqs, mean_psd))

                if freqs_ref is None:
                    freqs_ref = freqs

            if not per_file_psds:
                continue

            # Interpolate and average across files
            freqs_common = freqs_ref
            interpolated = []
            for fvec, pvec in per_file_psds:
                if not np.array_equal(fvec, freqs_common):
                    try:
                        p_interp = np.interp(freqs_common, fvec, pvec)
                    except Exception as e:
                        print(f"[WARN] Interpolation failed for {group_name}: {e}")
                        continue
                else:
                    p_interp = pvec
                interpolated.append(p_interp)

            if interpolated:
                group_mean = np.mean(np.vstack(interpolated), axis=0)
                groups.append((group_name, freqs_common, group_mean))

        self._psd_data = {g[0]: g[2] for g in groups}
        if groups:
            self._freqs = groups[0][1]

    def _extract_psd_fields(self, psd_struct):
        """Helper to safely extract freqs and values from MATLAB structs."""
        freqs, values = None, None
        try:
            if isinstance(psd_struct, dict):
                freqs = psd_struct.get("freqs")
                values = psd_struct.get("values")
            else:
                if hasattr(psd_struct, "freqs"):
                    freqs = psd_struct.freqs
                if hasattr(psd_struct, "values"):
                    values = psd_struct.values
        except Exception:
            pass
        return freqs, values

    def draw(self, colors: Dict[str, str] = None):
        """
        Draw all PSD groups on the same Axes.

        Args:
            group_colors: optional dict mapping group_name -> color string
        """
        self.clear()
        if not self._psd_data or self._freqs is None:
            print("[WARN] No PSD data to plot.")
            return

        line_style_raw = self.plot_params.get("line_style", "-")
        linestyle_map = {"solid": "-", "dashed": "--", "dotted": ":", "dashdot": "-."}
        line_style = linestyle_map.get(line_style_raw, "-")
        line_width = self.plot_params.get("line_width", 2)
        font_size = self.plot_params.get("font_size", 9)
        font_weight = self.plot_params.get("font_weight", "normal")
        title_size = self.plot_params.get("title_size", 11)
        title_weight = self.plot_params.get("title_weight", "bold")

        # Plot PSD
        for idx, (group_name, pxx) in enumerate(self._psd_data.items()):
            # Prefer color from draw argument
            if colors:
                color = colors[idx]
            # Otherwise check plot_params
            # elif "group_colors" in self.plot_params:
            #     color = self.plot_params["group_colors"][idx]
            else:
                color = None

            self.ax.plot(self._freqs, pxx, label=group_name, color=color, linestyle= line_style,
                         linewidth=line_width, alpha=0.9)


        # General settings
        self.ax.set_xlabel(self.plot_params.get("x_label", "Frequency (Hz)"), fontsize=font_size, fontweight=font_weight)
        self.ax.set_ylabel(self.plot_params.get("y_label", "Power"), fontsize=font_size, fontweight=font_weight)
        title = self.plot_params.get("title", "")
        xlim = self.plot_params.get("xlim", None)
        ylim = self.plot_params.get("ylim", None)
        if title:
            self.ax.set_title(title, fontsize=title_size, fontweight=title_weight)
        if xlim is not None:
            self.ax.set_xlim(xlim)
        if ylim is not None:
            self.ax.set_ylim(ylim)

        # Add shadows of different eeg bands
        bands = [
            (0, 4, 'Delta', '#a6cee3'),  # light blue
            (4, 8, 'Theta', '#b2df8a'),  # light green
            (8, 13, 'Alpha', '#fb9a99'),  # light red
            (13, 20, 'Beta 1', '#fdbf6f'),  # orange
            (20, 30, 'Beta 2', '#ff7f00'),  # darker orange
            (30, xlim[1], 'Gamma', '#cab2d6')  # light purple
        ]

        for start, end, label, color in bands:
            self.ax.axvspan(start, end, color=color, alpha=0.2, zorder=0)
            # x_pos = (start + end) / 2
            # y_pos = 0.9
            # self.ax.text(
            #     x_pos, y_pos, label,
            #     ha='center', va='top',
            #     fontsize=7,
            #     color='black', alpha=0.8, zorder=3,
            #     transform = self.ax.get_xaxis_transform()
            # )

        self.ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.6, zorder=0)
        self.ax.legend(frameon=False, fontsize=font_size)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
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
