from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import matplotlib.pyplot as plt


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
        self.last_limits = {
            "xlim": list(map(float, self.ax.get_xlim())),
            "ylim": list(map(float, self.ax.get_ylim()))
        }

    def get_last_limits(self):
        return self.last_limits