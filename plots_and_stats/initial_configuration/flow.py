# plots_and_stats/initial_configuration/flow.py
def validate_initial_configuration(controller, main_window):
    """
    Habilita o deshabilita el botón 'Next' según el estado actual del controller.
    """
    path_ok = getattr(controller, "existingPathCorrect", False)

    within_or_between = (
        controller.view.withinSubjectRadio.isChecked() or
        controller.view.betweenSubjectRadio.isChecked()
    )

    preprocessed_or_params = (
        controller.view.preprocessedRadio.isChecked() or
        controller.view.paramsRadio.isChecked()
    )

    enable_next = path_ok and within_or_between and preprocessed_or_params
    main_window.view.nextButton.setEnabled(enable_next)


def on_next_click(current_widget):
    """
    Es llamada automáticamente por el MainModuleWindowController
    cuando se hace clic en 'Next' desde este paso.
    Si no se cumplen las condiciones, bloquea el avance.
    """
    controller = getattr(current_widget, "controller", None)
    if controller is None:
        print("[Initial Config] No controller attached to widget.")
        return False, None

    # Comprobamos si todo está validado
    path_ok = getattr(controller, "existingPathCorrect", False)
    within_or_between = (
        controller.view.withinSubjectRadio.isChecked() or
        controller.view.betweenSubjectRadio.isChecked()
    )
    preprocessed_or_params = (
        controller.view.preprocessedRadio.isChecked() or
        controller.view.paramsRadio.isChecked()
    )

    if path_ok and within_or_between and preprocessed_or_params:
        # Todo correcto → permitir avanzar
        return True, {
            "experiment_info": controller.experiment_info,
            "selection": {
                "subject_mode": "within" if controller.view.withinSubjectRadio.isChecked() else "between",
                "data_type": "preprocessed" if controller.view.preprocessedRadio.isChecked() else "params"
            }
        }

    # Si no está todo correcto → bloquear avance
    print("[Initial Config] Validation failed, can't proceed.")
    return False, None
