def load_config(files_widget, data):

    # BIOSIGNAL INFO
    biosignal_txt = files_widget.biosignalBox.currentText()
    biosignal = biosignal_txt.split(" ")[1]
    files_widget.controller.biosignal_info = files_widget.controller.biosignals[biosignal]


    # PREPROCESSING
    prep_cfg = data["preprocessing"]
    preproc_widget = files_widget.main_window.stackedWidget.widget(2)  # widget(2) is the preprocessing widget
    preproc_widget.minbroadBox.setValue(prep_cfg['broadband_min'])
    preproc_widget.maxbroadBox.setValue(prep_cfg['broadband_max'])
    preproc_widget.preprocessingButton.setChecked(bool(prep_cfg["apply_preprocessing"]))
    preproc_widget.notchCBox.setChecked(bool(prep_cfg['notch']))
    preproc_widget.minfreqnotchBox.setValue(
        prep_cfg['notch_min'] if prep_cfg['notch_min'] is not None else preproc_widget.defaults["minfreqnotch"])
    preproc_widget.maxfreqnotchBox.setValue(
        prep_cfg['notch_max'] if prep_cfg['notch_max'] is not None else preproc_widget.defaults["minfreqnotch"])
    preproc_widget.orderNotchBox.setValue(
        prep_cfg['notch_order'] if prep_cfg['notch_order'] is not None else preproc_widget.defaults["ordernotch"])
    preproc_widget.winnotchBox.setCurrentText(prep_cfg['notch_win'])
    preproc_widget.bpCBox.setChecked(bool(prep_cfg['bandpass']))
    preproc_widget.minfreqbpBox.setValue(
        prep_cfg['bp_min'] if prep_cfg['bp_min'] is not None else preproc_widget.defaults["minfreqbp"])
    preproc_widget.maxfreqbpBox.setValue(
        prep_cfg['bp_max'] if prep_cfg['bp_max'] is not None else preproc_widget.defaults["maxfreqbp"])
    preproc_widget.orderbpBox.setValue(
        prep_cfg['bp_order'] if prep_cfg['bp_order'] is not None else preproc_widget.defaults["orderbp"])
    preproc_widget.winbpBox.setCurrentText(prep_cfg['bp_win'])
    preproc_widget.carCBox.setChecked(bool(prep_cfg['car']))
    preproc_widget.bandCBox.setChecked(bool(prep_cfg['band_segmentation']))
    preproc_widget.controller.update_band_label('segmentation', prep_cfg["selected_bands"])
    # Store
    files_widget.main_window.controller.preproc_config = prep_cfg

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
    segm_widget.normCBox.setChecked(bool(segm_cfg['norm']))
    if segm_cfg['norm_type'] == 'z':
        segm_widget.zscoreRButton.setChecked(True)  # RButton, so it is exclusive with dcRButton
    segm_widget.baselineCBox_1.setValue(
        segm_cfg['baseline_start'] if segm_cfg['baseline_start'] is not None else segm_widget.defaults['baselinewin1'])
    segm_widget.baselineCBox_2.setValue(
        segm_cfg['baseline_end'] if segm_cfg['baseline_end'] is not None else segm_widget.defaults['baselinewin2'])
    segm_widget.averageCBox.setChecked(bool(segm_cfg['average']))
    segm_widget.thresCBox.setChecked(bool(segm_cfg['thresholding']))
    segm_widget.threskBox.setValue(
        segm_cfg['thres_k'] if segm_cfg['thres_k'] is not None else segm_widget.defaults['threshold'])
    segm_widget.thressampBox.setValue(
        segm_cfg['thres_samples'] if segm_cfg['thres_samples'] is not None else segm_widget.defaults['thressamples'])
    segm_widget.threschanBox.setValue(
        segm_cfg['thres_channels'] if segm_cfg['thres_channels'] is not None else segm_widget.defaults['threschannels'])
    segm_widget.resampleCBox.setChecked(bool(segm_cfg['resample']))
    segm_widget.resamplefsBox.setValue(
        segm_cfg['resample_fs'] if segm_cfg['resample_fs'] is not None else segm_widget.defaults['resamplefs'])
    # Store
    files_widget.main_window.controller.segmentation_config = segm_cfg

    # PARAMETERS
    params_cfg = data["parameters"]
    params_widget = files_widget.main_window.stackedWidget.widget(4)  # widget(4) is the parameters widget
    params_widget.meanCBox.setChecked(bool(params_cfg['mean']))
    params_widget.medianCBox.setChecked(bool(params_cfg['median']))
    params_widget.varianceCBox.setChecked(bool(params_cfg['variance']))
    params_widget.kurtosisCBox.setChecked(bool(params_cfg['kurtosis']))
    params_widget.skewnessCBox.setChecked(bool(params_cfg['skewness']))
    params_widget.psdCBox.setChecked(bool(params_cfg['psd']))
    params_widget.segmentpsdBox.setValue(
        params_cfg['psd_segment_pct'] if params_cfg['psd_segment_pct'] is not None else params_widget.defaults[
            'psdsegment'])
    params_widget.overlappsdBox.setValue(
        params_cfg['psd_overlap_pct'] if params_cfg['psd_overlap_pct'] is not None else params_widget.defaults[
            'psdoverlap'])
    params_widget.psdcomboBox.setCurrentText(params_cfg['psd_window'])
    params_widget.rpCBox.setChecked(bool(params_cfg['relative_power']))
    params_widget.controller.update_band_label('rp', params_cfg["selected_rp_bands"])
    params_widget.apCBox.setChecked(bool(params_cfg['absolute_power']))
    params_widget.mfCBox.setChecked(bool(params_cfg['median_frequency']))
    params_widget.seCBox.setChecked(bool(params_cfg['spectral_entropy']))
    params_widget.ctmCBox.setChecked(bool(params_cfg['ctm']))
    params_widget.ctmrBox.setValue(
        params_cfg['ctm_r'] if params_cfg['ctm_r'] is not None else params_widget.defaults['ctmradius'])
    params_widget.sampenCBox.setChecked(bool(params_cfg['sample_entropy']))
    params_widget.sampenrBox.setValue(
        params_cfg['sample_entropy_r'] if params_cfg['sample_entropy_r'] is not None else params_widget.defaults[
            'sampradius'])
    params_widget.sampenmBox.setValue(
        params_cfg['sample_entropy_m'] if params_cfg['sample_entropy_m'] is not None else params_widget.defaults[
            'sampm'])
    params_widget.msampenCBox.setChecked(bool(params_cfg['multiscale_sample_entropy']))
    params_widget.msampenrBox.setValue(
        params_cfg['multiscale_sample_entropy_r'] if params_cfg['multiscale_sample_entropy_r'] is not None else
        params_widget.defaults['multisampradius'])
    params_widget.msampenmBox.setValue(
        params_cfg['multiscale_sample_entropy_m'] if params_cfg['multiscale_sample_entropy_m'] is not None else
        params_widget.defaults['multisampm'])
    params_widget.msampenscaleBox.setValue(
        params_cfg['multiscale_sample_entropy_scale'] if params_cfg['multiscale_sample_entropy_scale'] is not None else
        params_widget.defaults['multisampmaxscale'])
    params_widget.lzcCBox.setChecked(bool(params_cfg['lzc']))
    params_widget.mlzcCBox.setChecked(bool(params_cfg['multiscale_lzc']))
    if params_cfg['multiscale_lzc_scales'] is not None:
        params_widget.mlzcEdit.setText(str(params_cfg['multiscale_lzc_scales']))
    params_widget.iacCBox.setChecked(bool(params_cfg['iac']))
    params_widget.iacortButton.setChecked(bool(params_cfg['ort_iac']))
    params_widget.aecCBox.setChecked(bool(params_cfg['aec']))
    params_widget.aecortButton.setChecked(bool(params_cfg['ort_aec']))
    params_widget.pliCBox.setChecked(bool(params_cfg['pli']))
    params_widget.plvCBox.setChecked(bool(params_cfg['plv']))
    params_widget.wpliCBox.setChecked(bool(params_cfg['wpli']))
    params_widget.catchCBox.setChecked(bool(params_cfg['catch']))
    # Store
    files_widget.main_window.controller.parameters_config = params_cfg
