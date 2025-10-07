def load_config(files_widget, data):

    # PREPROCESSING
    prep_cfg = data["preprocessing"]
    preproc_widget = files_widget.main_window.stackedWidget.widget(2)  # widget(2) is the preprocessing widget
    preproc_widget.bandCBox.setChecked(prep_cfg['band_segmentation'] if prep_cfg['band_segmentation'] is not None else False)
    preproc_widget.minbroadBox.setValue(prep_cfg['broadband_min'])
    preproc_widget.maxbroadBox.setValue(prep_cfg['broadband_max'])
    preproc_widget.controller.update_band_label('segmentation', prep_cfg["selected_bands"])
    preproc_widget.preprocessingButton.setChecked(
        prep_cfg["apply_preprocessing"] if prep_cfg['apply_preprocessing'] is not None else False)
    preproc_widget.notchCBox.setChecked(prep_cfg['notch'] if prep_cfg['notch'] is not None else False)
    preproc_widget.minfreqnotchBox.setValue(
        prep_cfg['notch_min'] if prep_cfg['notch_min'] is not None else preproc_widget.defaults["minfreqnotch"])
    preproc_widget.maxfreqnotchBox.setValue(
        prep_cfg['notch_max'] if prep_cfg['notch_max'] is not None else preproc_widget.defaults["minfreqnotch"])
    preproc_widget.orderNotchBox.setValue(
        prep_cfg['notch_order'] if prep_cfg['notch_order'] is not None else preproc_widget.defaults["ordernotch"])
    preproc_widget.winnotchBox.setCurrentText(prep_cfg['notch_win'])
    preproc_widget.bpCBox.setChecked(prep_cfg['bandpass'] if prep_cfg['bandpass'] is not None else False)
    preproc_widget.minfreqbpBox.setValue(
        prep_cfg['bp_min'] if prep_cfg['bp_min'] is not None else preproc_widget.defaults["minfreqbp"])
    preproc_widget.maxfreqbpBox.setValue(
        prep_cfg['bp_max'] if prep_cfg['bp_max'] is not None else preproc_widget.defaults["maxfreqbp"])
    preproc_widget.orderbpBox.setValue(
        prep_cfg['bp_order'] if prep_cfg['bp_order'] is not None else preproc_widget.defaults["orderbp"])
    preproc_widget.winbpBox.setCurrentText(prep_cfg['bp_win'])
    preproc_widget.carCBox.setChecked(prep_cfg['car'] if prep_cfg['car'] is not None else False)

    # SEGMENTATION
    segm_cfg = data["segmentation"]
    segm_widget = files_widget.main_window.stackedWidget.widget(3)  # widget(3) is the segmentation widget
    segm_widget.conditionRButton.setChecked(
        segm_cfg['segmentation_type'] == 'condition')  # RButton, so it is exclusive with eventRButton
    segm_widget.trialBox.setValue(
        segm_cfg['trial_length'] if segm_cfg['trial_length'] is not None else segm_widget.defaults['triallength'])
    segm_widget.trialstrideBox.setValue(
        segm_cfg['trial_stride'] if segm_cfg['trial_stride'] is not None else segm_widget.defaults['trialstride'])
    segm_widget.winBox_1.setValue(
        segm_cfg['window_start'] if segm_cfg['window_start'] is not None else segm_widget.defaults['windowbox1'])
    segm_widget.winBox_2.setValue(
        segm_cfg['window_end'] if segm_cfg['window_end'] is not None else segm_widget.defaults['windowbox2'])
    segm_widget.normCBox.setChecked(segm_cfg['norm'] if segm_cfg['norm'] is not None else False)
    if segm_cfg['norm_type'] == 'z':
        segm_widget.zscoreRButton.setChecked(True)  # RButton, so it is exclusive with dcRButton
    segm_widget.baselineCBox_1.setValue(
        segm_cfg['baseline_start'] if segm_cfg['baseline_start'] is not None else segm_widget.defaults['baselinewin1'])
    segm_widget.baselineCBox_2.setValue(
        segm_cfg['baseline_end'] if segm_cfg['baseline_end'] is not None else segm_widget.defaults['baselinewin2'])
    segm_widget.averageCBox.setChecked(segm_cfg['average'] if segm_cfg['average'] is not None else False)
    segm_widget.thresCBox.setChecked(segm_cfg['thresholding'] if segm_cfg['thresholding'] is not None else False)
    segm_widget.threskBox.setValue(
        segm_cfg['thres_k'] if segm_cfg['thres_k'] is not None else segm_widget.defaults['threshold'])
    segm_widget.thressampBox.setValue(
        segm_cfg['thres_samples'] if segm_cfg['thres_samples'] is not None else segm_widget.defaults['thressamples'])
    segm_widget.threschanBox.setValue(
        segm_cfg['thres_channels'] if segm_cfg['thres_channels'] is not None else segm_widget.defaults['threschannels'])
    segm_widget.resampleCBox.setChecked(segm_cfg['resample'] if segm_cfg['resample'] is not None else False)
    segm_widget.resamplefsBox.setValue(
        segm_cfg['resample_fs'] if segm_cfg['resample_fs'] is not None else segm_widget.defaults['resamplefs'])

    # PARAMETERS
    params_cfg = data["parameters"]
    params_widget = files_widget.main_window.stackedWidget.widget(4)  # widget(4) is the parameters widget
    params_widget.meanCBox.setChecked(params_cfg['mean'] if params_cfg['mean'] is not None else False)
    params_widget.medianCBox.setChecked(params_cfg['median'] if params_cfg['median'] is not None else False)
    params_widget.varianceCBox.setChecked(params_cfg['variance'] if params_cfg['variance'] is not None else False)
    params_widget.kurtosisCBox.setChecked(params_cfg['kurtosis'] if params_cfg['kurtosis'] is not None else False)
    params_widget.skewnessCBox.setChecked(params_cfg['skewness'] if params_cfg['skewness'] is not None else False)
    params_widget.psdCBox.setChecked(params_cfg['psd'] if params_cfg['psd'] is not None else False)
    params_widget.segmentpsdBox.setValue(
        params_cfg['psd_segment_pct'] if params_cfg['psd_segment_pct'] is not None else params_widget.defaults[
            'psdsegment'])
    params_widget.overlappsdBox.setValue(
        params_cfg['psd_overlap_pct'] if params_cfg['psd_overlap_pct'] is not None else params_widget.defaults[
            'psdoverlap'])
    params_widget.psdcomboBox.setCurrentText(params_cfg['psd_window'])
    params_widget.rpCBox.setChecked(params_cfg['relative_power'] if params_cfg['relative_power'] is not None else False)
    params_widget.controller.update_band_label('rp', params_cfg["selected_rp_bands"])
    params_widget.apCBox.setChecked(params_cfg['absolute_power'] if params_cfg['absolute_power'] is not None else False)
    params_widget.mfCBox.setChecked(
        params_cfg['median_frequency'] if params_cfg['median_frequency'] is not None else False)
    params_widget.seCBox.setChecked(
        params_cfg['spectral_entropy'] if params_cfg['spectral_entropy'] is not None else False)
    params_widget.ctmCBox.setChecked(params_cfg['ctm'] if params_cfg['ctm'] is not None else False)
    params_widget.ctmrBox.setValue(
        params_cfg['ctm_r'] if params_cfg['ctm_r'] is not None else params_widget.defaults['ctmradius'])
    params_widget.sampenCBox.setChecked(
        params_cfg['sample_entropy'] if params_cfg['sample_entropy'] is not None else False)
    params_widget.sampenrBox.setValue(
        params_cfg['sample_entropy_r'] if params_cfg['sample_entropy_r'] is not None else params_widget.defaults[
            'sampradius'])
    params_widget.sampenmBox.setValue(
        params_cfg['sample_entropy_m'] if params_cfg['sample_entropy_m'] is not None else params_widget.defaults[
            'sampm'])
    params_widget.msampenCBox.setChecked(
        params_cfg['multiscale_sample_entropy'] if params_cfg['multiscale_sample_entropy'] is not None else False)
    params_widget.msampenrBox.setValue(
        params_cfg['multiscale_sample_entropy_r'] if params_cfg['multiscale_sample_entropy_r'] is not None else
        params_widget.defaults['multisampradius'])
    params_widget.msampenmBox.setValue(
        params_cfg['multiscale_sample_entropy_m'] if params_cfg['multiscale_sample_entropy_m'] is not None else
        params_widget.defaults['multisampm'])
    params_widget.msampenscaleBox.setValue(
        params_cfg['multiscale_sample_entropy_scale'] if params_cfg['multiscale_sample_entropy_scale'] is not None else
        params_widget.defaults['multisampmaxscale'])
    params_widget.lzcCBox.setChecked(params_cfg['lzc'] if params_cfg['lzc'] is not None else False)
    params_widget.mlzcCBox.setChecked(
        params_cfg['multiscale_lzc'] if params_cfg['multiscale_lzc'] is not None else False)
    if params_cfg['multiscale_lzc_scales'] is not None and params_cfg['multiscale_lzc_scales'].strip():
        params_widget.mlzcEdit.setText(str(params_cfg['multiscale_lzc_scales']))
    params_widget.iacCBox.setChecked(params_cfg['iac'] if params_cfg['iac'] is not None else False)
    params_widget.iacortButton.setChecked(params_cfg['ort_iac'] if params_cfg['ort_iac'] is not None else False)
    params_widget.aecCBox.setChecked(params_cfg['aec'] if params_cfg['aec'] is not None else False)
    params_widget.aecortButton.setChecked(params_cfg['ort_aec'] if params_cfg['ort_aec'] is not None else False)
    params_widget.pliCBox.setChecked(params_cfg['pli'] if params_cfg['pli'] is not None else False)
    params_widget.plvCBox.setChecked(params_cfg['plv'] if params_cfg['plv'] is not None else False)
    params_widget.wpliCBox.setChecked(params_cfg['wpli'] if params_cfg['wpli'] is not None else False)