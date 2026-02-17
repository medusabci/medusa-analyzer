from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import matplotlib.pyplot as plt
import numpy as np
from typing import List, Optional

class BasePlot(ABC):
    """
    Abstract base class for plot types.
    Provides a standard interface for updating and clearing plots.
    """

    def __init__(self, ax: plt.Axes, plot_params: Optional[Dict[str, Any]] = None):
        self.ax = ax
        self.plot_params = plot_params or {}
        self.last_limits = {} # save info from the last draw

    @abstractmethod
    def load_data(self, *args, **kwargs):
        """Load and preprocess data specific to the plot type."""
        pass

    @abstractmethod
    def draw(self):
        """Render the plot on the assigned Axes."""
        pass

    def clear(self):
        """Clear the current axis."""
        self.ax.clear()
        self.apply_labels()
        self.apply_title()

    def apply_labels(self):
        font_size = self.plot_params.get("font_size", 10)
        font_weight = self.plot_params.get("font_weight", "normal")

        self.ax.set_xlabel(
            self.plot_params.get("x_label", ""),
            fontsize=font_size,
            fontweight=font_weight
        )
        self.ax.set_ylabel(
            self.plot_params.get("y_label", ""),
            fontsize=font_size,
            fontweight=font_weight
        )

    def apply_title(self):
        title = self.plot_params.get("title", "")
        if not title:
            return

        self.ax.set_title(
            title,
            fontsize=self.plot_params.get("title_size", 12),
            fontweight=self.plot_params.get("title_weight", "bold")
        )

    def get_font(self):
        return {
            "fontsize": self.plot_params.get("font_size", 10),
            "fontweight": self.plot_params.get("font_weight", "normal")
        }

    def apply_grid_and_spines(self, axis="both"):
        self.ax.grid(True, axis=axis, linestyle="--", alpha=0.4)
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)

    def safe_set_lim(self, method, lim):
        if not isinstance(lim, (list, tuple)) or len(lim) != 2:
            return

        lo, hi = lim
        if lo is None and hi is None:
            return

        try:
            ax_method = getattr(self.ax, method)
            cur_lo, cur_hi = ax_method()
            ax_method([
                lo if lo is not None else cur_lo,
                hi if hi is not None else cur_hi
            ])
        except Exception as e:
            print(f"[WARN] Could not apply {method}: {e}")

    def save_limits(self):
        self.last_limits = {"xlim": list(map(float, self.ax.get_xlim())), "ylim": list(map(float, self.ax.get_ylim()))}

    def get_last_limits(self):
        return self.last_limits

    def normalize_data(self, data: np.ndarray, selected_channels: Optional[List[int]] = None ) -> np.ndarray:
        """
        Normalize data to shape (channels,).

        Accepted shapes:
        - (channels,)
        - (1, channels)
        - (epochs, channels)

        If epochs dimension exists, average over epochs.
        """

        if data is None:
            return None

        data = np.asarray(data)

        # Case 1: already channels vector
        if data.ndim == 1:
            return data

        # Case 2: 2D matrix
        if data.ndim == 2:
            # shape: 1 x channels
            if data.shape[0] == 1:
                return data.squeeze()

            # shape: epochs x channels
            return np.mean(data, axis=0)

        # Case 3: 3D tensor (epochs x channels x something_else)
        if data.ndim == 3:
            return np.mean(data, axis=0)
        else:
            raise ValueError(f"[BasePlot] Unsupported data shape: {data.shape}")

    def normalize_data_psd(self, values: np.ndarray) -> np.ndarray:
        """
        Normalize PSD data to shape (freqs, channels).

        Accepted shapes:
        - (freqs, channels)
        - (channels, freqs)
        - (epochs, freqs, channels)
        """

        values = np.asarray(values)

        # Case 1: freqs x channels
        if values.ndim == 2:
            return values

        # Case 2: epochs x freqs x channels
        if values.ndim == 3:
            return np.mean(values, axis=0)

        raise ValueError(f"[PSDPlot] Unsupported PSD shape: {values.shape}")
