import numpy as np
import medusa.transforms
from medusa.signal_metrics import (band_power, median_frequency, shannon_spectral_entropy, central_tendency,
                                   sample_entropy, multiscale_entropy, lempelziv_complexity,
                                   multiscale_lempelziv_complexity)
from medusa.connectivity_metrics import plv, pli, wpli, aec, iac
from scipy.stats import kurtosis, skew

def compute_parameters(epoched, settings, fs, band):
    params = {}

    # --- Estadísticos básicos ---
    stat_funcs = {
        'mean': np.mean,
        'variance': np.var,
        'median': np.median,
        'kurtosis': kurtosis,
        'skewness': skew
    }
    axis = 0 if epoched.ndim == 2 else 1
    avg = settings['segmentation']['average']
    for name, func in stat_funcs.items():
        if settings['parameters'].get(name, False):
            val = func(epoched, axis=axis)
            params[name] = np.mean(val, axis=0) if avg and epoched.ndim == 3 else val

    # --- Cálculo único de PSD si es necesario ---
    needs_psd = any([
        settings['parameters'].get(k, False)
        for k in ['relative_power', 'absolute_power', 'median_frequency', 'spectral_entropy']
    ])
    if needs_psd and (band == 'broadband' or band is None):
        fxx, psd = medusa.transforms.power_spectral_density(epoched, fs)

    # --- Relative Power ---
    if settings['parameters'].get('relative_power', False) and (band == 'broadband' or band is None):
        bb = [settings['parameters']['broadband_min'], settings['parameters']['broadband_max']]
        norm_psd = medusa.transforms.normalize_psd(psd, bb, fxx, norm='rel')
        params['norm_psd'] = norm_psd
        for b in settings['parameters']['selected_rp_bands']:
            val = medusa.signal_metrics.band_power.band_power(norm_psd, fs, [b['min'], b['max']])
            params[f"relative_power_{b.get('name', 'unknown')}"] = np.nanmean(val, axis=0) if avg else val

    # --- Absolute Power ---
    if settings['parameters'].get('absolute_power', False) and (band == 'broadband' or band is None):
        for b in settings['parameters']['selected_ap_bands']:
            val = medusa.signal_metrics.band_power.band_power(psd, fs, [b['min'], b['max']])
            params[f"absolute_power_{b.get('name', 'unknown')}"] = np.nanmean(val, axis=0) if avg else val

    # --- Median Frequency ---
    if settings['parameters'].get('median_frequency', False) and (band == 'broadband' or band is None):
        for b in settings['parameters']['selected_mf_bands']:
            val = medusa.signal_metrics.median_frequency.median_frequency(psd, fs, [b['min'], b['max']])
            params[f"median_frequency_{b.get('name', 'unknown')}"] = np.nanmean(val, axis=0) if avg else val

    # --- Spectral Entropy ---
    if settings['parameters'].get('spectral_entropy', False) and (band == 'broadband' or band is None):
        for b in settings['parameters']['selected_se_bands']:
            val = medusa.signal_metrics.shannon_spectral_entropy.shannon_spectral_entropy(psd, fs, [b['min'], b['max']])
            params[f"spectral_entropy_{b.get('name', 'unknown')}"] = np.nanmean(val, axis=0) if avg else val

    # --- Non linear and connectivity parameters ---
    param_map = {
        'ctm': lambda: medusa.signal_metrics.central_tendency.central_tendency_measure(epoched,
                                                                                       settings['parameters']['ctm_r']),
        'sample_entropy': lambda: medusa.signal_metrics.sample_entropy.sample_entropy(epoched,
                                                                                      settings['parameters'][
                                                                                          'sample_entropy_m'],
                                                                                      settings['parameters'][
                                                                                          'sample_entropy_r']),
        'multiscale_sample_entropy': lambda: medusa.signal_metrics.multiscale_entropy.multiscale_entropy(
            epoched, settings['parameters']['multiscale_sample_entropy_scale'],
            settings['parameters']['multiscale_sample_entropy_m'],
            settings['parameters']['multiscale_sample_entropy_r']),
        'lzc': lambda: medusa.signal_metrics.lempelziv_complexity.lempelziv_complexity(epoched),
        'multiscale_lzc': lambda: medusa.signal_metrics.multiscale_lempelziv_complexity.multiscale_lempelziv_complexity(
            epoched,
            settings['parameters']['multiscale_lzc_scales']),
        'iac': lambda: medusa.connectivity_metrics.iac(epoched, settings['parameters']['ort_iac']),
        'aec': lambda: medusa.connectivity_metrics.aec(epoched, settings['parameters']['ort_aec']),
        'plv': lambda: medusa.connectivity_metrics.plv(epoched),
        'pli': lambda: medusa.connectivity_metrics.pli(epoched),
        'wpli': lambda: medusa.connectivity_metrics.wpli(epoched),
    }

    for name, func in param_map.items():
        if settings['parameters'].get(name, False):
            val = func()
            params[name] = np.nanmean(val, axis=0) if avg else val

    return params