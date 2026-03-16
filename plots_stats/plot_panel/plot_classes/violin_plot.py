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

    def __init__(self, ax, plot_params=None, main_module=None):
        super().__init__(ax, plot_params, main_module=main_module)
        self._group_values = {}
        self._stats_signature = None

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

        new_signature = self._build_stats_signature()
        if new_signature != self._stats_signature:
            self.statistical_results = None
            self.statistical_report = ""

        self._stats_signature = new_signature
        self._sync_main_module_stats_payload()

    def get_stats_payload(self):
        groups = []
        data = []

        for group_name, values in self._group_values.items():
            curr_values = np.asarray(values, dtype=float).tolist()
            data.extend(curr_values)
            groups.extend([group_name] * len(curr_values))

        if not data or len(set(groups)) < 2:
            return None

        return {
            "data": np.asarray(data, dtype=float),
            "groups": np.asarray(groups, dtype=object),
            "signature": self._stats_signature,
        }

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

        self._draw_stats_annotations(df, group_order)

        # Save final Y limits
        self.safe_set_lim("set_ylim", self.plot_params.get("ylim"))
        self.apply_grid_and_spines(axis="y")
        self.save_limits()

    def _build_stats_signature(self):
        signature = []
        for group_name in sorted(self._group_values):
            values = tuple(np.round(np.asarray(self._group_values[group_name], dtype=float), 12).tolist())
            signature.append((group_name, values))
        return tuple(signature)

    def _sync_main_module_stats_payload(self):
        if self.main_module is None:
            return

        payload = self.get_stats_payload()
        if payload is None:
            self.main_module.data_stats = np.array([])
            self.main_module.group_stats = np.array([])
            self.main_module.statistical_source_signature = None
        else:
            self.main_module.data_stats = payload["data"]
            self.main_module.group_stats = payload["groups"]
            self.main_module.statistical_source_signature = payload["signature"]

        self.main_module.statistical_source_plot = self
        self.main_module.statistical_results = self.statistical_results
        self.main_module.statistical_report = self.statistical_report

    def _draw_stats_annotations(self, df: pd.DataFrame, group_order: List[str]):
        if not isinstance(self.statistical_results, dict):
            return

        pairwise_res = self.statistical_results.get("pairwise", {}) or {}
        if not pairwise_res:
            return

        pairs = list(itertools.combinations(group_order, 2))
        if not pairs:
            return

        y_max = df["value"].max()
        y_min = df["value"].min()
        if pd.isna(y_max) or pd.isna(y_min):
            return

        y_range = y_max - y_min
        if y_range == 0:
            y_range = abs(y_max) if y_max != 0 else 1.0

        h_line = y_max + 0.05 * y_range
        step = 0.08 * y_range
        line_count = 0

        for g1, g2 in pairs:
            result = pairwise_res.get((g1, g2)) or pairwise_res.get((g2, g1))
            if not result:
                continue

            p_adj = self._extract_p_value(result)
            label = self._get_significance_label(p_adj)
            if label is None:
                continue

            x1, x2 = group_order.index(g1), group_order.index(g2)
            curr_h = h_line + (line_count * step)

            self.ax.plot(
                [x1, x1, x2, x2],
                [curr_h, curr_h + step * 0.15, curr_h + step * 0.15, curr_h],
                lw=1.2,
                c="#222222",
            )
            self.ax.text(
                (x1 + x2) * 0.5,
                curr_h + step * 0.15,
                label,
                ha="center",
                va="bottom",
                color="#222222",
                fontsize=12,
            )
            line_count += 1

    def _extract_p_value(self, result: Dict[str, float]):
        for key in ("p_values_corr", "p_values"):
            value = result.get(key)
            if value is None:
                continue
            if isinstance(value, str) and value == "":
                continue
            try:
                return float(np.asarray(value).squeeze())
            except (TypeError, ValueError):
                continue
        return None

    def _get_significance_label(self, p_value):
        if p_value is None or p_value >= 0.05:
            return None
        if p_value < 0.001:
            return "***"
        if p_value < 0.01:
            return "**"
        return "*"
