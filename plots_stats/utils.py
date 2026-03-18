import numpy as np
import pandas as pd
from scipy import stats
import itertools
import pingouin as pg
from PySide6.QtWidgets import (QPushButton, QVBoxLayout, QHBoxLayout, QDialog,
                               QPlainTextEdit, QFileDialog, QMessageBox)
from PySide6.QtGui import QFont

class StatsReport(QDialog):
    def __init__(self, text_report, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Statistical Analysis Report")
        self.resize(550, 550)
        self.text_report = text_report

        layout = QVBoxLayout(self)

        # Área de texto
        self.text_viewer = QPlainTextEdit()
        self.text_viewer.setReadOnly(True)
        self.text_viewer.setPlainText(self.text_report)

        font = QFont("Courier")
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.text_viewer.setFont(font)

        layout.addWidget(self.text_viewer)

        # Buttons
        layout_buttons = QHBoxLayout()
        self.btn_save = QPushButton("Save report")
        self.btn_close = QPushButton("Close")

        layout_buttons.addWidget(self.btn_save)
        layout_buttons.addWidget(self.btn_close)

        layout.addLayout(layout_buttons)

        # Conexiones
        self.btn_close.clicked.connect(self.close)
        self.btn_save.clicked.connect(self.save_report)

    def save_report(self):
        path_file, _ = QFileDialog.getSaveFileName(
            self,
            "Save Report",
            "statistical_report.txt",
            "Text files (*.txt);All files (*)"
        )

        if path_file:
            try:
                with open(path_file, 'w', encoding='utf-8') as f:
                    f.write(self.text_report)
                QMessageBox.information(self, "Success", "Report successfully saved.")
                self.close()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Report could not be saved:\n{str(e)}")


def do_stats(data, groups, paired=True, padjust=None, is_continuous=False):
    """
    Single flow statistical analysis for both discrete and continuous data.
    padjust: str, optional. 'bonf' (Bonferroni), 'fdr_bh' (Benjamini-Hochberg FDR) or None.
    is_continuous: bool, if True expects data to have timepoints in axis=1.
    """
    data = np.array(data)
    groups = np.array(groups)

    # 1. UNIFY DIMENSIONS FOR SINGLE FLOW
    # If discrete, we expand dimensions to (samples, 1) so the loop runs exactly once.
    if not is_continuous:
        if data.ndim == 1:
            data = np.expand_dims(data, axis=1)
        else:
            raise ValueError("If is_continuous is False, data must be 1D.")
    else:
        if data.ndim != 2:
            raise ValueError("If is_continuous is True, data must be 2D (samples x timepoints).")

    n_samples, n_timepoints = data.shape
    unique_groups = np.unique(groups)
    n_groups = len(unique_groups)

    if n_groups < 2:
        raise ValueError(f"Statistical analysis requires at least two groups. Found: {n_groups}")

    # 2. ASSUMPTIONS CHECK
    all_normal = True
    all_homoscedastic = True

    for t in range(n_timepoints):
        # Extract data for each group at time t
        group_data_t = [data[groups == g, t] for g in unique_groups]

        # Check equal lengths for within-subjects analysis (only needed once)
        if paired and t == 0:
            lengths = [len(gd) for gd in group_data_t]
            if len(set(lengths)) > 1:
                raise ValueError("Within subjects analysis requires equal observations per group.")

        # Normality check (Shapiro Wilk test)
        if all_normal:
            for gd in group_data_t:
                if len(gd) >= 3:
                    _, p_val = stats.shapiro(gd)
                    if p_val < 0.05:
                        all_normal = False
                        break
                else:
                    all_normal = False
                    break

        # Homoscedasticity check (Levene's test)
        if all_normal and all_homoscedastic and n_groups > 1:
            _, p_val = stats.levene(*group_data_t)
            if p_val < 0.05:
                all_homoscedastic = False

        # Optimization: break early if both assumptions already failed
        if not all_normal and not all_homoscedastic:
            break

    is_parametric = all_normal and all_homoscedastic

    # 3. INITIALIZE STORAGE
    omnibus_res = None
    if n_groups > 2:
        omnibus_res = {
            'p_values': np.zeros(n_timepoints),
            'stats': np.zeros(n_timepoints),
            'test': ''
        }

    pairs = list(itertools.combinations(range(n_groups), 2))
    pairwise_res = {
        (unique_groups[i], unique_groups[j]): {
            'p_values': np.zeros(n_timepoints),
            'stats': np.zeros(n_timepoints),
            'test': ''
        } for i, j in pairs
    }

    # 3. STATISTICAL TESTS (Unified Loop)
    for t in range(n_timepoints):
        group_data_t = [data[groups == g, t] for g in unique_groups]

        # 3.a OMNIBUS TEST (Only if n_groups > 2)
        if n_groups > 2:
            if is_parametric:
                if paired:
                    df_t = pd.DataFrame({'data': data[:, t], 'group': groups})
                    df_t['subject'] = df_t.groupby('group').cumcount()
                    aov = pg.rm_anova(data=df_t, dv='data', within='group', subject='subject', detailed=False)
                    omnibus_res['stats'][t] = aov['F'].values[0]
                    omnibus_res['p_values'][t] = aov['p_unc'].values[0]
                    omnibus_res['test'] = 'Repeated Measures ANOVA'
                else:
                    stat, p = stats.f_oneway(*group_data_t)
                    omnibus_res['stats'][t] = stat
                    omnibus_res['p_values'][t] = p
                    omnibus_res['test'] = 'One-way ANOVA'
            else:
                if paired:
                    stat, p = stats.friedmanchisquare(*group_data_t)
                    omnibus_res['test'] = 'Friedman'
                else:
                    stat, p = stats.kruskal(*group_data_t)
                    omnibus_res['test'] = 'Kruskal-Wallis'
                omnibus_res['stats'][t] = stat
                omnibus_res['p_values'][t] = p

        # 3.b PAIRWISE TESTS
        if not (is_continuous and n_groups > 2):
            for i, j in pairs:
                g1, g2 = unique_groups[i], unique_groups[j]
                d1, d2 = group_data_t[i], group_data_t[j]

                if is_parametric:
                    if paired:
                        stat, p = stats.ttest_rel(d1, d2)
                        test_applied = 'Paired t-test'
                    else:
                        stat, p = stats.ttest_ind(d1, d2)
                        test_applied = 'Independent t-test'
                else:
                    if paired:
                        stat, p = stats.wilcoxon(d1, d2)
                        test_applied = 'Wilcoxon signed-rank'
                    else:
                        stat, p = stats.mannwhitneyu(d1, d2)
                        test_applied = 'Mann-Whitney U'

                pairwise_res[(g1, g2)]['stats'][t] = stat
                pairwise_res[(g1, g2)]['p_values'][t] = p
                pairwise_res[(g1, g2)]['test'] = test_applied

    # 4. P-VALUE CORRECTION
    adj_name = "None"
    if is_continuous:
        output_pvalues = np.zeros(n_timepoints)
    if padjust is not None and padjust.lower() != 'none':
        pair_keys = list(pairwise_res.keys())

        # Identify correction method
        if padjust.lower() in ['bonf', 'bonferroni']:
            method = 'bonf'
            adj_name = 'Bonferroni'
        elif padjust.lower() in ['fdr_bh', 'bh', 'fdr']:
            method = 'fdr_bh'
            adj_name = 'Benjamini-Hochberg FDR'
        else:
            raise ValueError("padjust parameter must be 'bonf', 'fdr_bh', or None")

        # Apply correction
        if is_continuous:
            if n_groups > 2:
                p_vals_time = omnibus_res['p_values']
                _, p_corr_time = pg.multicomp(p_vals_time, method=method)
                omnibus_res['p_values_corr'] = p_corr_time
                output_pvalues = p_corr_time
            else:
                p_vals_time = pairwise_res[pair_keys[0]]['p_values']
                _, p_corr_time = pg.multicomp(p_vals_time, method=method)
                pairwise_res[pair_keys[0]]['p_values_corr'] = p_corr_time
                output_pvalues = p_corr_time
        elif n_groups > 2:
            # Correct across all the group pairs
            all_p_discrete = np.array([pairwise_res[k]['p_values'][0] for k in pair_keys])
            _, p_corr_discrete = pg.multicomp(all_p_discrete, method=method)

            # Store the corrected p-values in their comparison
            for idx, k in enumerate(pair_keys):
                # Se guarda como array 1D para mantener la compatibilidad con el desempaquetado final
                pairwise_res[k]['p_values_corr'] = np.array([p_corr_discrete[idx]])
        else:
            # Else (if correction makes no sense), store an empty value
            for k in pairwise_res.keys():
                pairwise_res[k]['p_values_corr'] = ''
                adj_name = 'None'
    else:
        # Else (if no correction), store an empty value
        for k in pairwise_res.keys():
            if is_continuous:
                output_pvalues = pairwise_res[k]['p_values']
                break
            pairwise_res[k]['p_values_corr'] = ''

    if is_continuous:
        # Skip report and return only the p-values of interest
        return output_pvalues, ''

    # 5. TEXT REPORT GENERATION
    lines = []
    lines.append("=" * 60)
    title = " STATISTICAL ANALYSIS REPORT "
    lines.append(title.center(60))
    lines.append("=" * 60 + "\n")

    lines.append("1. ASSUMPTIONS CHECK:")
    lines.append(f"   - Normality: {all_normal}")
    if all_normal:
        lines.append(f"   - Homoscedasticity: {all_homoscedastic}")
    else:
        lines.append(f"   - Homoscedasticity: Not evaluated (Normality failed)")

    test_type = "PARAMETRIC" if is_parametric else "NON-PARAMETRIC"
    lines.append(f"   -> Decision: {test_type} tests applied.\n")

    lines.append("2. TESTS APPLIED:")

    if omnibus_res is not None:
        lines.append("   [OMNIBUS TEST]")
        lines.append(f"   - Test applied: {omnibus_res['test']}")
        lines.append(f"   - Statistic: {omnibus_res['stats'][0]:.4f}")
        lines.append(f"   - p-value: {omnibus_res['p_values'][0]:.4e}")
        lines.append("")

    lines.append("   [PAIRWISE COMPARISONS]")
    lines.append(f"   - p-value correction method: {adj_name}")
    for k, res in pairwise_res.items():
        lines.append(f"   --- Comparison: {k[0]} vs {k[1]} ---")
        lines.append(f"       Test: {res['test']}")
        lines.append(f"       Statistic: {res['stats'][0]:.4f}")
        lines.append(f"       Raw p-value: {res['p_values'][0]:.4e}")
        if adj_name != "None":
            lines.append(f"       Corrected p-value: {res['p_values_corr'][0]:.4e}")

    report_text = "\n".join(lines)

    # 6. RETURN LOGIC
    # Unpack arrays if discrete so the user gets single floats instead of arrays of length 1
    if omnibus_res:
        omnibus_res['stats'] = omnibus_res['stats'][0]
        omnibus_res['p_values'] = omnibus_res['p_values'][0]

    for k in pairwise_res.keys():
        pairwise_res[k]['stats'] = pairwise_res[k]['stats'][0]
        pairwise_res[k]['p_values'] = pairwise_res[k]['p_values'][0]
        if pairwise_res[k]['p_values_corr']:
            pairwise_res[k]['p_values_corr'] = pairwise_res[k]['p_values_corr'][0]

    return_dict = {
        'assumptions': {
            'is_normal': all_normal,
            'is_homoscedastic': all_homoscedastic,
            'use_parametric': is_parametric
        },
        'omnibus': omnibus_res,
        'pairwise': pairwise_res
    }

    return return_dict, report_text