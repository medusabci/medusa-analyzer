from typing import Optional, Dict, Any, Tuple
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from medusa.plots.head_plots import TopographicPlot as MedusaTopographicPlot

"""
Wrappers for different plot types used in the PlotPanel.

Available plot classes:
    - PSDPlot: Plot Power Spectral Density (PSD) data.
    - TopographicPlot: Plot topographic maps of EEG data. Uses medusa's head_plots module.
"""
class PSDPlot:
    """
    Class for plotting Power Spectral Density (PSD) data.
    Constructor:
        ax: matplotlib.axes.Axes
        plot_params: optional dict with plot parameters:
            - x_label, y_label, color, title
    User methods:
        p = PSDPlot(ax, plot_params)
    """

    def __init__(self, ax: Axes, plot_params: Optional[Dict[str, Any]] = None):
        self.ax = ax
        self.plot_params = plot_params or {}
        self._line = None
        self._freqs = None
        self._psd = None

        # Aplicar labels / título inicial
        x_label = self.plot_params.get("x_label", "Frequency (Hz)")
        y_label = self.plot_params.get("y_label", "Power")
        title = self.plot_params.get("title", "")
        xlim = self.plot_params.get("xlim", None)
        ylim = self.plot_params.get("ylim", None)
        self.ax.set_xlabel(x_label)
        self.ax.set_ylabel(y_label)
        if title:
            self.ax.set_title(title)

        # Clear axis
        self.ax.clear()
        # Re-apply labels after clear
        self.ax.set_xlabel(x_label)
        self.ax.set_ylabel(y_label)
        if title:
            self.ax.set_title(title)
        if xlim is not None:
            try:
                self.ax.set_xlim(xlim)
            except Exception as e:
                print(f"[WARN] Failed to set xlim: {e}")
        if ylim is not None:
            try:
                self.ax.set_ylim(ylim)
            except Exception as e:
                print(f"[WARN] Failed to set ylim: {e}")

class TopographicPlotWrapper:
    """
    Wrapper class for Medusa's TopographicPlot to be used in PlotPanel.
    Constructor:
        ax: matplotlib.axes.Axes
        plot_params: optional dict with plot parameters:
            - x_label, y_label, color_map, colorbar_min, colorbar_max, interpolate (bool),
              interp_neighbors, interp_points, interp_contour_width, channel_radius_size, etc.
    User methods:
        topo = TopographicPlotWrapper(ax, plot_params)
        topo.update(values)
        to.clear()
    """

    def __init__(self, ax: Axes, channel_set, plot_params: Optional[Dict[str, Any]] = None):
        self.ax = ax
        self.channel_set = channel_set
        self.plot_params = plot_params or {}
        self._medusa_topo: Optional[MedusaTopographicPlot] = None
        self._cbar = None

        # Preparar argumentos compatibles con MedusaTopographicPlot
        medusa_kwargs = {
            "axes": self.ax,
            "channel_set": self.channel_set,
            "cmap": self.plot_params.get("color_map", self.plot_params.get("cmap", "YlGnBu_r")),
            "clim": None,  # lo configuramos cuando actualicemos si vienen límites
            "interpolate": self.plot_params.get("interpolate", True),
            "interp_neighbors": self.plot_params.get("interp_neighbors", 3),
            "interp_points": self.plot_params.get("interp_points", 500),
            "interp_contour_width": self.plot_params.get("interp_contour_width", 0.8),
            "channel_radius_size": self.plot_params.get("channel_radius_size", None),
            "plot_channel_points": self.plot_params.get("plot_channel_points", True),
            "plot_channel_labels": self.plot_params.get("plot_channel_labels", False),
        }

        # Inicializar el objeto medusa (sin datos aún)
        self._medusa_topo = MedusaTopographicPlot(**medusa_kwargs)