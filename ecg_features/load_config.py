from PySide6 import QtWidgets
def load_config(files_widget, data):
    """
    Loads configuration from a saved JSON-like dict for the ECG processing module.
    """

    # BIOSIGNAL INFO
    biosignal_txt = files_widget.biosignalBox.currentText()
    biosignal = biosignal_txt.split(" ")[1]
    files_widget.controller.biosignal_info = files_widget.controller.biosignals[biosignal]

    # --- LEADS ---
    # lead_cfg = data["leads"]
    # leads_widget = files_widget.main_window.stackedWidget.widget(2)
    # # Set selected leads
    # selected_leads = lead_cfg.get("selected_leads", {})
    # if hasattr(leads_widget, "controller"):
    #     leads_widget.controller.selected_leads = selected_leads
    #     leads_widget.controller.selected_conditions = lead_cfg.get("selected_conditions", [])
    #
    # layout = leads_widget.LeadsSelection.layout()
    # if layout is None:
    #     return
    # for i in range(layout.count()):
    #     row_widget = layout.itemAt(i).widget()
    #     if not row_widget:
    #         continue
    #
    #     checkbox = row_widget.findChild(QtWidgets.QCheckBox)
    #     combo = row_widget.findChild(QtWidgets.QComboBox)
    #
    #     if not checkbox or not combo:
    #         continue
    #
    #     channel_name = checkbox.text().replace("Channel ", "").strip()
    #     if channel_name in selected_leads:
    #         checkbox.setChecked(True)
    #         desired_lead = selected_leads[channel_name]
    #         index = combo.findText(desired_lead)
    #         if index != -1:
    #             combo.setCurrentIndex(index)
    #     else:
    #         checkbox.setChecked(False)
    #
    # if len(selected_leads) == 1:
    #     leads_widget.leadLabel.setText(list(selected_leads.values())[0])
    # elif len(selected_leads) > 1:
    #     leads_widget.leadLabel.setText(", ".join(selected_leads.values()))
    # else:
    #     leads_widget.leadLabel.clear()

    # --- PREPROCESSING ---
    prep_cfg = data["preprocessing"]
    preproc_widget = files_widget.main_window.stackedWidget.widget(3)  # widget(3): preprocessing
    controller = preproc_widget.controller
    preproc_widget.cleanCBox.setChecked(prep_cfg.get("clean", False))
    preproc_widget.zscoreCBox.setChecked(prep_cfg.get("zscore", False))
    preproc_widget.hrvCBox.setChecked(prep_cfg.get("hrv", False))
    preproc_widget.cleanBox.setCurrentText(prep_cfg.get("processing_method", "neurokit"))
    preproc_widget.artifactsCBox.setChecked(prep_cfg.get("correct_artifacts", False))
    if "resample_fs" in prep_cfg:
        preproc_widget.resampleBox.setValue(prep_cfg["resample_fs"])
    files_widget.main_window.controller.preproc_config = prep_cfg

    # --- PARAMETERS ---
    params_cfg = data["parameters"]
    params_widget = files_widget.main_window.stackedWidget.widget(4)  # widget(4): parameters
    params_controller = params_widget.controller

    # Set general analysis options
    params_widget.pulserateCBox.setChecked(bool(params_cfg.get("pulse_rate", False)))
    params_widget.avnnCBox.setChecked(bool(params_cfg.get("average", False)))
    params_widget.sdnnCBox.setChecked(bool(params_cfg.get("std_nn", False)))
    params_widget.rmssdCBox.setChecked(bool(params_cfg.get("rms_sucessive_diff", False)))
    params_widget.sdsdCBox.setChecked(bool(params_cfg.get("std_sucessive_diff", False)))
    params_widget.vcCBox.setChecked(bool(params_cfg.get("variation_coef", False)))
    params_widget.tinnCBox.setChecked(bool(params_cfg.get("tring_interp", False)))
    params_widget.pnn20CBox.setChecked(bool(params_cfg.get("pnn20", False)))
    params_widget.pnn50CBox.setChecked(bool(params_cfg.get("pnn50", False)))
    params_widget.psdCBox.setChecked(bool(params_cfg.get("psd", False)))
    params_widget.svbCBox.setChecked(bool(params_cfg.get("sympathovagal_balance", False)))
    params_widget.controller.update_band_label(params_cfg["selected_bands"])
    params_widget.powerCBox.setChecked(bool(params_cfg.get("power", False)))
    params_widget.kurtCBox.setChecked(bool(params_cfg.get("kurtosis", False)))
    params_widget.skewnessCBox.setChecked(bool(params_cfg.get("skewness", False)))
    params_widget.mfCBox.setChecked(bool(params_cfg.get("median_frequency", False)))
    params_widget.seCBox.setChecked(bool(params_cfg.get("spectral_entropy", False)))
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
    params_widget.shaeCBox.setChecked(bool(params_cfg.get("shannon_entropy", False)))
    params_widget.lzcCBox.setChecked(bool(params_cfg.get("lzc", False)))
    params_widget.dfaCBox.setChecked(
        params_cfg['dfa'] if params_cfg['dfa'] is not None else False)
    params_widget.dfanBox.setValue(
        params_cfg['dfa_n'] if params_cfg['dfa_n'] is not None else params_widget.defaults[
            'dfan'])
    params_widget.dfabBox.setValue(
        params_cfg['dfa_b'] if params_cfg['dfa_b'] is not None else params_widget.defaults[
            'dfab'])
    params_widget.poincareCBox.setChecked(bool(params_cfg.get("poincare", False)))

    files_widget.main_window.controller.parameters_config = params_cfg