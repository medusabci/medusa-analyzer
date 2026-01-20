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
        self._data_cache = {}
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
        self.ax.set_xlabel(self.plot_params.get("x_label", ""))
        self.ax.set_ylabel(self.plot_params.get("y_label", ""))
        title = self.plot_params.get("title", "")
        if title:
            self.ax.set_title(title)

    def get_last_limits(self):
        return self.last_limits