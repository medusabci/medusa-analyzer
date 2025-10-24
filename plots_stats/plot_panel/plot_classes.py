from typing import Optional, Dict, Any, Tuple
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from medusa.plots.head_plots import TopographicPlot as MedusaTopographicPlot
# TODO: BORRAR
"""
Wrappers for different plot types used in the PlotPanel.

Available plot classes:
    - PSDPlot: Plot Power Spectral Density (PSD) data.
    - TopographicPlot: Plot topographic maps of EEG data. Uses medusa's head_plots module.
"""

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