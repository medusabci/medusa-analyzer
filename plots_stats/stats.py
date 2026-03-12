import numpy as np
import pandas as pd
from scipy import stats
import itertools
import pingouin as pg


def do_stats(data, groups, paired=True, padjust=None, save_path=None):
    """
    padjust: str, optional. 'bonf' (Bonferroni), 'fdr_bh' (Benjamini-Hochberg FDR) or None.
    """
    # Create a DataFrame for easier data manipulation
    df = pd.DataFrame({'data': data, 'group': groups})

    # Add subject ID for paired analysis (needed for pingouin's rm_anova)
    if paired:
        df['subject'] = df.groupby('group').cumcount()

    # Extract unique groups and their data
    unique_groups = df['group'].unique()
    n_groups = len(unique_groups)

    # Store the data arrays for each group in a list
    group_data = [df[df['group'] == g]['data'].values for g in unique_groups]

    # Check if paired data has matching lengths across groups
    if paired:
        lengths = [len(gd) for gd in group_data]
        if len(set(lengths)) > 1:
            raise ValueError("Within subjects analysis (paired statistical tests). This implies that all groups must "
                             "have the same number of observations.")

    # 1. ASSUMPTIONS CHECK
    is_normal = True
    for gd in group_data:
        if len(gd) >= 3:  # Shapiro requires at least 3 data points
            stat, p_val = stats.shapiro(gd)
            if p_val < 0.05:
                is_normal = False
                break
        else:
            is_normal = False

    is_homoscedastic = False
    if is_normal:
        if n_groups > 1:
            stat, p_val = stats.levene(*group_data)
            if p_val >= 0.05:
                is_homoscedastic = True

    is_parametric = is_normal and is_homoscedastic

    results = {
        'assumptions': {
            'is_normal': is_normal,
            'is_homoscedastic': is_homoscedastic,
            'use_parametric': is_parametric
        },
        'omnibus': None,
        'pairwise': []
    }

    # 2. OMNIBUS TEST
    if n_groups > 2:
        if is_parametric:
            if paired:
                aov = pg.rm_anova(data=df, dv='data', within='group', subject='subject', detailed=False)
                p_val = aov['p-unc'].values[0]
                f_stat = aov['F'].values[0]
                results['omnibus'] = {'test': 'Repeated Measures ANOVA', 'statistic': f_stat, 'p_value': p_val}
            else:
                stat, p = stats.f_oneway(*group_data)
                results['omnibus'] = {'test': 'One-way ANOVA', 'statistic': stat, 'p_value': p}
        else:
            if paired:
                stat, p = stats.friedmanchisquare(*group_data)
                results['omnibus'] = {'test': 'Friedman', 'statistic': stat, 'p_value': p}
            else:
                stat, p = stats.kruskal(*group_data)
                results['omnibus'] = {'test': 'Kruskal-Wallis', 'statistic': stat, 'p_value': p}

    # 3. PAIRWISE TESTS
    pairs = list(itertools.combinations(range(n_groups), 2))

    for i, j in pairs:
        g1, g2 = unique_groups[i], unique_groups[j]
        d1, d2 = group_data[i], group_data[j]

        if is_parametric:
            if paired:
                stat, p = stats.ttest_rel(d1, d2)
                test_name = 'Paired t-test'
            else:
                stat, p = stats.ttest_ind(d1, d2)
                test_name = 'Independent t-test'
        else:
            if paired:
                stat, p = stats.wilcoxon(d1, d2)
                test_name = 'Wilcoxon signed-rank'
            else:
                stat, p = stats.mannwhitneyu(d1, d2)
                test_name = 'Mann-Whitney U'

        results['pairwise'].append({
            'group1': g1,
            'group2': g2,
            'test': test_name,
            'statistic': stat,
            'p_value': p
        })

    # 4. P-VALUE CORRECTION
    adj_name = "None"
    if padjust is not None and padjust.lower() != 'none':
        pvals = [res['p_value'] for res in results['pairwise']]

        if padjust.lower() in ['bonf', 'bonferroni']:
            reject, pvals_corr = pg.multicomp(pvals, method='bonf')
            adj_name = 'Bonferroni'
        elif padjust.lower() in ['fdr_bh', 'bh', 'fdr']:
            reject, pvals_corr = pg.multicomp(pvals, method='fdr_bh')
            adj_name = 'Benjamini-Hochberg FDR'
        else:
            raise ValueError("padjust parameter must be 'bonf', 'fdr_bh', or None")

        for idx, res in enumerate(results['pairwise']):
            res['p_value_corr'] = pvals_corr[idx]
            res['correction'] = adj_name

    # 5. TEXT REPORT GENERATION
    lines = []
    lines.append("=" * 60)
    lines.append(" STATISTICAL ANALYSIS REPORT ".center(60))
    lines.append("=" * 60 + "\n")

    # Assumptions
    lines.append("1. ASSUMPTIONS CHECK:")
    lines.append(f"   - Normality: {is_normal}")
    if is_normal:
        lines.append(f"   - Homoscedasticity: {is_homoscedastic}")
    else:
        lines.append("   - Homoscedasticity: Not evaluated (Normality failed)")

    test_type = "PARAMETRIC" if is_parametric else "NON-PARAMETRIC"
    lines.append(f"   -> Decision: {test_type} tests will be applied.\n")

    # Omnibus
    if results['omnibus']:
        lines.append("2. OMNIBUS TEST (Global comparison):")
        lines.append(f"   - Test applied: {results['omnibus']['test']}")
        lines.append(f"   - Statistic: {results['omnibus']['statistic']:.4f}")
        lines.append(f"   - p-value: {results['omnibus']['p_value']:.4e}\n")
    else:
        lines.append("2. OMNIBUS TEST: Not applicable (2 or fewer groups).\n")

    # Pairwise
    lines.append("3. PAIRWISE COMPARISONS:")
    lines.append(f"   - p-value correction method: {adj_name}\n")

    for res in results['pairwise']:
        lines.append(f"   --- Group {res['group1']} vs Group {res['group2']} ---")
        lines.append(f"       Test: {res['test']}")
        lines.append(f"       Statistic: {res['statistic']:.4f}")
        lines.append(f"       Raw p-value: {res['p_value']:.4e}")
        if 'p_value_corr' in res:
            lines.append(f"       Corrected p-value ({adj_name}): {res['p_value_corr']:.4e}")
        lines.append("")

    report_text = "\n".join(lines)

    # Print to CMD
    print(report_text)

    if save_path is not None:
        try:
            with open(save_path + '/StatisticalReport.txt', 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"\n>>> Report successfully saved to: {save_path + '/StatisticalReport.txt'}")
        except Exception as e:
            print(f"\n>>> Error saving the file: {e}")

    return results