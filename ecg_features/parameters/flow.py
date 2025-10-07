from PySide6 import QtWidgets

def get_parameters_config(controller):
    """
   Collects the current configuration of parameters from the UI.
   """
    # Configuration dict
    config = {
        "averege": True if controller.view.avnnCBox.isChecked() else None,
        "std_nn": True if controller.view.sdnnCBox.isChecked() else None,
        "rms_sucessive_diff": True if controller.view.rmssdCBox.isChecked() else None,
        "std_sucessive_diff": True if controller.view.sdsdCBox.isChecked() else None,
        "variation_coef": True if controller.view.vcCBox.isChecked() else None,
        "tring_interp": True if controller.view.tinnCBox.isChecked() else None,
        "pnn50": True if controller.view.pnn50CBox.isChecked() else None,
        "pnn20": True if controller.view.pnn20CBox.isChecked() else None,
        "psd": True if controller.view.psdCBox.isChecked() else None,
        "sympathovagal_balance": True if controller.view.svbCBox.isChecked() else None,
        "selected_bands": controller.selected_bands if controller.selected_bands else None,
        "power": True if controller.view.powerCBox.isChecked() else None,
        "kurtosis": True if controller.view.kurtCBox.isChecked() else None,
        "skewness": True if controller.view.skewnessCBox.isChecked() else None,
        "median_frequency": True if controller.view.mfCBox.isChecked() else None,
        "spectral_entropy": True if controller.view.seCBox.isChecked() else None,
        "ctm": True if controller.view.ctmCBox.isChecked() else None,
        "ctm_r": controller.view.ctmrBox.value() if controller.view.ctmCBox.isChecked() else None,
        "sample_entropy": True if controller.view.sampenCBox.isChecked() else None,
        "sample_entropy_r": controller.view.sampenrBox.value() if controller.view.sampenCBox.isChecked() else None,
        "sample_entropy_m": controller.view.sampenmBox.value() if controller.view.sampenCBox.isChecked() else None,
        "shannon_entropy": True if controller.view.shaeCBox.isChecked() else None,
        "lzc": True if controller.view.lzcCBox.isChecked() else None,
        "dfa": True if controller.view.dfaCBox.isChecked() else None,
        "dfa_n": controller.view.dfanBox.value() if controller.view.dfaCBox.isChecked() else None,
        "dfa_b": controller.view.dfabBox.value() if controller.view.dfaCBox.isChecked() else None,
        "poincare": True if controller.view.poincareCBox.isChecked() else None,
    }
    return config

def on_next_click(view):
    """
    Handles the event when the "Next" button is clicked. It initializes the save widget,
    """

    # If not selected bands and spectral parameters are selected, show error
    if not view.controller.selected_bands and (view.powerCBox.isChecked() or view.kurtCBox.isChecked() or
           view.skewnessCBox.isChecked() or view.mfCBox.isChecked() or view.seCBox.isChecked()):
        QtWidgets.QMessageBox.critical(view,
        "Invalid configuration",
        "To compute spectral parameters of HRV, you must select at least one frequency band. "
        "Please click the 'Edit bands' to choose one or more bands."
        )
        return False

    # If PSD is not selected and any of the spectral parameters is selected, show warning
    if not view.psdCBox.isChecked() and (view.svbCBox.isChecked() or view.powerCBox.isChecked() or view.kurtCBox.isChecked()
                            or view.skewnessCBox.isChecked() or view.mfCBox.isChecked() or view.seCBox.isChecked()):
        QtWidgets.QMessageBox.warning(view,
        "Warning with PSD configuration",
                                      "You have selected at least one spectral parameter, but the Power Spectral "
                                      "Density (PSD) computation is not enabled. Default parameters (PSD length % of the"
                                      " trial: 80, overlap %: 50, and window: boxcar) will be used for the PSD "
                                      "calculation. Please ensure that these parameters are appropriate for your "
                                      "analysis."
        )

    # Save config
    view.main_window.controller.parameters_config = get_parameters_config(view.controller)

    return True

