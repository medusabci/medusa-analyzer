import numpy as np
import scipy.io
import pandas as pd
import seaborn as sns
import matplotlib.colors as mcolors
from typing import Dict, List
from .base_plot import BasePlot
import itertools

class ViolinPlot(BasePlot):
    """
    Violin plot for per-group distributions (Seaborn backend).
    """

    def __init__(self, ax, plot_params=None):
        super().__init__(ax, plot_params)
        self._group_values = {}

    def load_data(self, filtered_files: Dict[str, List[str]], selected_channels: List[int]):

        self._group_values.clear()
        for group_name, file_list in filtered_files.items():
            values = []

            for filepath in file_list:
                try:
                    mat = scipy.io.loadmat(filepath, squeeze_me=True, struct_as_record=False)
                except Exception as e:
                    print(f"[ERROR] Cannot load {filepath}: {e}")
                    continue

                data = None
                for key in ("data", "vector", "values", "valores", "param"):
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

                data = self.normalize_data(data)
                max_idx = data.shape[0] - 1
                valid_channels = [ch for ch in selected_channels if 0 <= ch <= max_idx] or [0]
                values.append(np.mean(data[valid_channels]))

            if values:
                self._group_values[group_name] = np.asarray(values)

    def draw(self, colors=None):
        self.clear()

        if not self._group_values:
            print("[WARN] No ViolinPlot data to plot.")
            return

        # Create a dataframe for seaborn
        df = pd.DataFrame([{"group": g, "value": v} for g, vals in self._group_values.items() for v in vals])

        # Obtain colors for each group
        group_order = list(self._group_values.keys())
        violin_alpha = self.plot_params.get("violin_transparency", 0.6)
        palette = None
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
            saturation=1,
            zorder = 1
        )

        plot_strip = bool(self.plot_params.get("plot_strip", True))
        if plot_strip:
            # Strip
            sns.stripplot(
                data=df,
                x='group',
                y="value",
                hue='group',
                order=group_order,
                ax=self.ax,
                palette=palette,
                edgecolor='#000000',
                linewidth=0.3,
                size=7,
                jitter=True,
                alpha=0.7,
                zorder=10,
                legend=False
            )

        # Boxplot overlay optional
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
                boxprops={"facecolor": "none", "zorder": 20},
                medianprops={"color": "black", "linewidth": 1.5},
                whiskerprops={"linewidth": 1},
                capprops={"linewidth": 1, "zorder": 20},
            )

        # ---- Mean / Median lines (optional) ----
        plot_mean = bool(self.plot_params.get("plot_mean_line", False))
        plot_median = bool(self.plot_params.get("plot_median_line", False))

        if plot_mean or plot_median:
            means = df.groupby("group")["value"].mean()
            medians = df.groupby("group")["value"].median()

            half_width = 0.25  # controls line length inside violin
            for i, g in enumerate(group_order):
                if plot_mean and g in means:
                    self.ax.hlines(
                        y=means[g],
                        xmin=i - half_width,
                        xmax=i + half_width,
                        colors="black",
                        linestyles="--",
                        linewidth=1.2,
                        zorder=2
                    )

                if plot_median and g in medians:
                    self.ax.hlines(
                        y=medians[g],
                        xmin=i - half_width,
                        xmax=i + half_width,
                        colors="black",
                        linestyles=":",
                        linewidth=1.2,
                        zorder=2
                    )

        # Get whether to show the stats bars
        stats_checkbox = False

        if stats_checkbox:

            # Run the statistical analysis if it has not been done yet
            if not self.statistical_results in locals():
                self.view.main_module.plot_panel.controller.stats_report()

            # Pairs of groups
            pairs = list(itertools.combinations(group_order, 2))

            # Generate random values for testing
            pairwise_res = {}
            for g1, g2 in pairs:
                pairwise_res[(g1, g2)]['p_values_corr'] = np.random.uniform(0, 0.3)

            # Get the y range for establishing the y position of the horizontal bars showing the significance
            y_max = df["value"].max()
            if pd.isna(y_max): return
            y_range = y_max - df["value"].min()
            h_line = y_max + 0.02 * y_range
            step = 0.08 * y_range

            # For each comparison
            line_count = 0
            for g1, g2 in pairs:

                # If exits the corrected p-values, use them, otherwise use the original ones
                if pairwise_res[(g1, g2)]['p_values_corr']:
                    p_adj = pairwise_res[(g1, g2)]['p_values_corr']
                else:
                    p_adj = pairwise_res[(g1, g2)]['p_values']

                # Label as a function of the significance level
                if p_adj < 0.05:
                    if p_adj < 0.001:
                        label = '***'
                    elif p_adj < 0.01:
                        label = '**'
                    else:
                        label = '*'

                    # Get the positions of the current groups for plotting
                    x1, x2 = group_order.index(g1), group_order.index(g2)
                    curr_h = h_line + (line_count * step)

                    # Plot the line and the label
                    self.ax.plot([x1, x1, x2, x2], [curr_h, curr_h + step * 0.15, curr_h + step * 0.15, curr_h],
                            lw=1.2, c='#222222')
                    self.ax.text((x1 + x2) * .5, curr_h + step * 0.15, label, ha='center', va='bottom',
                            color='#222222', fontsize=12)
                    line_count += 1


        # Save final Y limits
        self.safe_set_lim("set_ylim", self.plot_params.get("ylim"))
        self.apply_grid_and_spines(axis="y")
        self.save_limits()
