import ast
from PySide6 import QtWidgets

def get_parameters_config(controller):
    """
   Collects the current configuration of parameters from the UI.
   """
    # Configuration dict
    config = {
        "mean": True if controller.view.meanCBox.isChecked() else None,
        "median": True if controller.view.medianCBox.isChecked() else None,
        "variance": True if controller.view.varianceCBox.isChecked() else None,
        "kurtosis": True if controller.view.kurtosisCBox.isChecked() else None,
        "skewness": True if controller.view.skewnessCBox.isChecked() else None,
        "psd": True if controller.view.psdCBox.isChecked() else None,
        "psd_segment_pct": controller.view.segmentpsdBox.value() if controller.view.psdCBox.isChecked() else None,
        "psd_overlap_pct": controller.view.overlappsdBox.value() if controller.view.psdCBox.isChecked() else None,
        'psd_window': controller.view.psdcomboBox.currentText() if controller.view.psdCBox.isChecked() else None,
        "relative_power": True if controller.view.rpCBox.isChecked() else None,
        "selected_rp_bands": controller.selected_bands_by_type["rp"] if controller.view.rpCBox.isChecked() else None,
        "absolute_power": True if controller.view.apCBox.isChecked() else None,
        "median_frequency": True if controller.view.mfCBox.isChecked() else None,
        "spectral_entropy": True if controller.view.seCBox.isChecked() else None,
        "ctm": True if controller.view.ctmCBox.isChecked() else None,
        "ctm_r": controller.view.ctmrBox.value() if controller.view.ctmCBox.isChecked() else None,
        "sample_entropy": True if controller.view.sampenCBox.isChecked() else None,
        "sample_entropy_r": controller.view.sampenrBox.value() if controller.view.sampenCBox.isChecked() else None,
        "sample_entropy_m": controller.view.sampenmBox.value() if controller.view.sampenCBox.isChecked() else None,
        "multiscale_sample_entropy": True if controller.view.msampenCBox.isChecked() else None,
        "multiscale_sample_entropy_r": controller.view.msampenrBox.value() if controller.view.msampenCBox.isChecked() else None,
        "multiscale_sample_entropy_m": controller.view.msampenmBox.value() if controller.view.msampenCBox.isChecked() else None,
        "multiscale_sample_entropy_scale": controller.view.msampenscaleBox.value() if controller.view.msampenCBox.isChecked() else None,
        "lzc": True if controller.view.lzcCBox.isChecked() else None,
        "multiscale_lzc": True if controller.view.mlzcCBox.isChecked() else None,
        "multiscale_lzc_scales": ast.literal_eval(controller.view.mlzcEdit.text()) if controller.view.mlzcCBox.isChecked()
                                                                                and controller.view.mlzcEdit.text().strip() else None,
        "iac": True if controller.view.iacCBox.isChecked() else None,
        "ort_iac": True if controller.view.iacortButton.isChecked() and controller.view.iacCBox.isChecked() else None,
        "aec": True if controller.view.aecCBox.isChecked() else None,
        "ort_aec": True if controller.view.aecortButton.isChecked() and controller.view.aecCBox.isChecked() else None,
        "pli": True if controller.view.pliCBox.isChecked() else None,
        "plv": True if controller.view.plvCBox.isChecked() else None,
        "wpli": True if controller.view.wpliCBox.isChecked() else None
    }
    return config

def on_next_click(view):
    """
    Handles the event when the "Next" button is clicked. It initializes the save widget,
    """
    preprocessing_widget = view.main_window.stackedWidget.widget(2)
    rp_bands = view.controller.selected_bands_by_type.get('rp', [])
    if view.rpCBox.isChecked() and not preprocessing_widget.bandCBox.isChecked() and not rp_bands:
        QtWidgets.QMessageBox.critical(
            view,
            "Invalid configuration",
            "To compute the Relative Power, you must select at least one frequency band. "
            "Please click the 'Edit bands' to choose one or more bands "
            "before enabling the calculation of relative power."
        )
        return False
    # Save config
    view.main_window.controller.parameters_config = get_parameters_config(view.controller)

    # If no preprocessing is selected, disable the option to save preprocessed signals
    if not preprocessing_widget.preprocessingButton.isChecked():
        save_widget = view.main_window.stackedWidget.widget(5)
        save_widget.prepsignalsCBox.setVisible(False)

    return True

