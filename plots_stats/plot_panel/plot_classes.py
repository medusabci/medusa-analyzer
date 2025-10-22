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
        p.update(signa)
        p.clear()
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


    def update(self, freqs, pxx):
        """Plot PSD data."""

        self._freqs = freqs
        self._psd = pxx

        self.ax.cla() # clear axis

        x_label = self.plot_params.get("x_label", "Frequency (Hz)")
        y_label = self.plot_params.get("y_label", "Power")
        title = self.plot_params.get("title", "")
        self.ax.set_xlabel(x_label)
        self.ax.set_ylabel(y_label)
        if title:
            self.ax.set_title(title)

        line_kwargs = {}
        if "color" in self.plot_params:
            line_kwargs["color"] = self.plot_params["color"]

        self._line, = self.ax.plot(freqs, pxx, **line_kwargs)

        # Optional: set x limits
        xlim = self.plot_params.get("xlim", None)
        if xlim:
            self.ax.set_xlim(xlim)

        self.ax.relim()
        self.ax.autoscale_view()

    def clear(self):
        """Clear axis."""
        if self._line is not None:
            try:
                self._line.remove()
            except Exception:
                pass
            self._line = None
        self.ax.cla()
        self.ax.set_xlabel(self.plot_params.get("x_label", "Frequency (Hz)"))
        self.ax.set_ylabel(self.plot_params.get("y_label", "Power"))
        if self.plot_params.get("title", ""):
            self.ax.set_title(self.plot_params.get("title", ""))



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

    def update(self, values):
        """Actualiza la topografía con un array 'values' (len = n_channels)."""
        values = np.asarray(values).squeeze()
        if values.ndim != 1 or values.size != len(self.channel_set.channels):
            raise ValueError("values must be 1D array with same length as channel_set.channels")

        # Configurar clim si viene en plot_params
        cmin = self.plot_params.get("colorbar_min", None)
        cmax = self.plot_params.get("colorbar_max", None)
        if cmin is not None or cmax is not None:
            clim = [cmin if cmin is not None else np.min(values),
                    cmax if cmax is not None else np.max(values)]
            # setear clim en el objeto medusa (usa atributo clim en __init__)
            self._medusa_topo.cmap = self.plot_params.get("color_map", self._medusa_topo.cmap)
            self._medusa_topo.clim = clim
        else:
            # si no hay límites, dejamos que Medusa calcule min/max
            self._medusa_topo.clim = None
            self._medusa_topo.cmap = self.plot_params.get("color_map", self._medusa_topo.cmap)

        # Hacemos update (medusa crea handles internamente)
        self._medusa_topo.update(values)

        # (Re)crear / actualizar colorbar si procede
        # El objeto medusa_topo.plot_handles['color-mesh'] puede ser:
        # - para interpolation: un PolyMesh (mappable)
        # - para no-interpolate: mapper (ScalarMappable) guardado en 'color-mesh'
        # Intentaremos usarlo para colorbar.
        try:
            # eliminar colorbar previo
            if self._cbar is not None:
                try:
                    self._cbar.remove()
                except Exception:
                    pass
                self._cbar = None

            # Obtener mappable
            ph = self._medusa_topo.plot_handles
            mappable = None
            if ph is not None and 'color-mesh' in ph:
                mappable = ph['color-mesh']

            if mappable is not None:
                # Si es mapper (ScalarMappable) o QuadMesh, podemos añadir colorbar
                fig = self.ax.figure
                # crear un axes pequeño a la derecha y poner colorbar allí
                # Intentamos usar una posición estándar si no existe
                cax = fig.add_axes([0.92, 0.12, 0.02, 0.76])  # puede ajustarse en el layout del caller
                # Si mappable es un ScalarMappable: fig.colorbar(mappable, cax=cax)
                # Si es un PolyCollection/pcolormesh tendrá el mismo comportamiento
                self._cbar = fig.colorbar(mappable, cax=cax)
        except Exception:
            # No rompemos si el colorbar falla; lo dejamos sin colorbar
            pass

        # Forzar redraw del axes
        self.ax.relim()
        self.ax.autoscale_view()

    def clear(self):
        """Limpia la topografía (borra handles y colorbar)."""
        if self._medusa_topo is not None:
            try:
                self._medusa_topo.clear()
            except Exception:
                pass
        if self._cbar is not None:
            try:
                self._cbar.remove()
            except Exception:
                pass
            self._cbar = None
        # dejar el axes limpio
        try:
            self.ax.cla()
        except Exception:
            pass