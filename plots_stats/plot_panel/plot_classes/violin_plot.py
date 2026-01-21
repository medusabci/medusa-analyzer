import numpy as np
import scipy.io
import pandas as pd
import seaborn as sns
import matplotlib.colors as mcolors
from typing import Dict, List
from .base_plot import BasePlot


class ViolinPlot(BasePlot):
    """
    Violin plot for per-group distributions (Seaborn backend).
    """

    def __init__(self, ax, plot_params=None):
        super().__init__(ax, plot_params)
        self._group_values = {}

    def load_data(
        self,
        filtered_files: Dict[str, List[str]],
        selected_channels: List[int],
    ):
        self._group_values.clear()

        for group_name, file_list in filtered_files.items():
            values = []

            for filepath in file_list:
                try:
                    mat = scipy.io.loadmat(
                        filepath, squeeze_me=True, struct_as_record=False
                    )
                except Exception as e:
                    print(f"[ERROR] Cannot load {filepath}: {e}")
                    continue

                data = None
                for key in ("data", "vector", "values", "valores"):
                    if key in mat:
                        data = np.asarray(mat[key]).squeeze()
                        break

                if data is None:
                    for v in mat.values():
                        if isinstance(v, np.ndarray) and v.ndim == 1:
                            data = v
                            break

                if data is None:
                    continue

                valid_channels = [ch for ch in selected_channels if 0 <= ch < data.size]
                if not valid_channels:
                    valid_channels = [0]

                values.append(np.mean(data[valid_channels]))

            if values:
                self._group_values[group_name] = np.asarray(values)

    def draw(self, colors=None):
        self.clear()

        if not self._group_values:
            print("[WARN] No ViolinPlot data to plot.")
            return

        # Create a dataframe for seaborn
        rows = []
        for group, vals in self._group_values.items():
            for v in vals:
                rows.append({"group": group, "value": v})
        df = pd.DataFrame(rows)

        # Obtain colors for each group
        group_order = list(self._group_values.keys())
        violin_alpha = self.plot_params.get("violin_transparency", 0.6)
        if isinstance(colors, dict):
            palette = {g: mcolors.to_rgba(colors.get(g, "#999999"), alpha=violin_alpha) for g in group_order}

        # Plot violin
        sns.violinplot(
            data=df,
            x="group",
            y="value",
            hue="group",
            order=group_order,
            ax=self.ax,
            palette=palette,
            inner=None,
            cut=2,
            linewidth=1,
            saturation=1
        )

        # Boxplot overlay opcional
        plot_boxplot = bool(self.plot_params.get("plot_boxplot", True))
        if plot_boxplot:
            sns.boxplot(
                data=df,
                x="group",
                y="value",
                order=group_order,
                ax=self.ax,
                width=0.15,
                showcaps=True,
                showfliers=False,
                boxprops={"facecolor": "white", "zorder": 3},
                medianprops={"color": "black", "linewidth": 1.5},
                whiskerprops={"linewidth": 1},
                capprops={"linewidth": 1, "zorder": 10},
            )

        # ---- Mean / Median lines (optional) ----
        plot_mean = bool(self.plot_params.get("plot_mean_line", False))
        plot_median = bool(self.plot_params.get("plot_median_line", False))

        if plot_mean or plot_median:
            means = df.groupby("group")["value"].mean()
            medians = df.groupby("group")["value"].median()

            line_color = self.plot_params.get("stat_line_color", "black")
            line_width = self.plot_params.get("stat_line_width", 1.2)
            mean_ls = self.plot_params.get("mean_line_style", "--")
            median_ls = self.plot_params.get("median_line_style", ":")

            half_width = 0.25  # controls line length inside violin

            for i, g in enumerate(group_order):
                if plot_mean and g in means:
                    self.ax.hlines(
                        y=means[g],
                        xmin=i - half_width,
                        xmax=i + half_width,
                        colors=line_color,
                        linestyles=mean_ls,
                        linewidth=line_width,
                        zorder=2
                    )

                if plot_median and g in medians:
                    self.ax.hlines(
                        y=medians[g],
                        xmin=i - half_width,
                        xmax=i + half_width,
                        colors=line_color,
                        linestyles=median_ls,
                        linewidth=line_width,
                        zorder=2
                    )

        # Save final Y limits
        y_min, y_max = self.ax.get_ylim()
        self.last_limits = {"ylim": [float(y_min), float(y_max)]}

        # Labels & fonts
        font_size = self.plot_params.get("font_size", 10)
        font_weight = self.plot_params.get("font_weight", "normal")

        self.ax.set_xlabel(
            self.plot_params.get("x_label", "Groups"),
            fontsize=font_size,
            fontweight=font_weight
        )
        self.ax.set_ylabel(
            self.plot_params.get("y_label", "Value"),
            fontsize=font_size,
            fontweight=font_weight
        )

        self.ax.tick_params(axis='x', rotation=45)
        for label in self.ax.get_xticklabels():
            label.set_fontsize(font_size)
            label.set_fontweight(font_weight)

        title = self.plot_params.get("title", "")
        if title:
            self.ax.set_title(
                title,
                fontsize=self.plot_params.get("title_size", 14),
                fontweight=self.plot_params.get("title_weight", "normal")
            )

        self._safe_set_lim(self.ax, "set_ylim", self.plot_params.get("ylim", None))
        self.ax.grid(True, axis="y", linestyle="--", alpha=0.4)
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)

    def _safe_set_lim(self, ax, method, lim):
        if not isinstance(lim, (list, tuple)) or len(lim) != 2:
            return
        lo, hi = lim
        if lo is None and hi is None:
            return
        try:
            ax_method = getattr(ax, method)
            cur_lo, cur_hi = ax_method()
            ax_method([
                lo if lo is not None else cur_lo,
                hi if hi is not None else cur_hi
            ])
        except Exception as e:
            print(f"[WARN] Could not apply {method}: {e}")
