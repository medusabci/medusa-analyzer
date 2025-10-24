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

        for group_name, pxx in self._psd_data.items():
            color = None
            # Prefer color from draw argument
            if colors and group_name in colors:
                color = colors[group_name]
            # Otherwise check plot_params
            elif "group_colors" in self.plot_params and group_name in self.plot_params["group_colors"]:
                color = self.plot_params["group_colors"][group_name]

            self.ax.plot(self._freqs, pxx, label=group_name, color=color)

        self.ax.set_xlabel(self.plot_params.get("x_label", "Frequency (Hz)"))
        self.ax.set_ylabel(self.plot_params.get("y_label", "Power"))
        title = self.plot_params.get("title", "")
        xlim = self.plot_params.get("xlim", None)
        ylim = self.plot_params.get("ylim", None)
        if title:
            self.ax.set_title(title)
        if xlim is not None:
            self.ax.set_xlim(xlim)
        if ylim is not None:
            self.ax.set_ylim(ylim)

        self.ax.legend()
        self.ax.relim()
        self.ax.autoscale_view()
