def apply_preprocessing(signal, fs, cfg):
    import medusa.transforms
    if cfg.get('bandpass') and None not in (cfg.get('bp_min'), cfg.get('bp_max'), cfg.get('bp_order')):
        signal = medusa.FIRFilter(cfg['bp_order'], [cfg['bp_min'], cfg['bp_max']], 'bandpass').fit_transform(
            signal, fs)
    if cfg.get('notch') and None not in (cfg.get('notch_min'), cfg.get('notch_max'), cfg.get('notch_order')):
        signal = medusa.FIRFilter(cfg['notch_order'], [cfg['notch_min'], cfg['notch_max']],
                                  'bandstop').fit_transform(signal, fs)
    return medusa.car(signal) if cfg.get('car') else signal


def band_segmentation(signal, bp_min, bp_max, fs):
    import medusa.transforms
    bp_filter = medusa.FIRFilter(1000, [bp_min, bp_max], 'bandpass')
    signal = bp_filter.fit_transform(signal, fs)
    return signal