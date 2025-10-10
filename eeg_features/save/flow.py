from eeg_features.utils import run_pipeline
from PySide6 import QtWidgets

def handle_exceptions(func):
    """
    Decorator that manages exceptions raised inside UI actions. Logs the error if possible, otherwise prints it.
    """

    def wrapper(self, *args, **kwargs):
        # Try to run the function
        try:
            return func(self, *args, **kwargs)
        # If Exception
        except Exception as e:
            # Log the error with the custom format, if possible
            if hasattr(self, 'log_message'):
                self._log_message(f"[ERROR] {func.__name__}: {str(e)}", style='error')
            # Otherwise, print it
            else:
                print(f"[ERROR] {func.__name__}: {str(e)}")

            # To vaoid closing the app
            return False

    return wrapper


@handle_exceptions # Decorator to handle exceptions and log them
def on_next_click(view):
    """
    Handles the event when the "Next" button is clicked. It runs the pipeline and shows a message box upon completion.
    """
    # If the pipeline has not already been completed, run it
    if not view.controller.pipeline_completed:

        # If no folder is selected, show a warning and return
        if not view.selected_folder:
            QtWidgets.QMessageBox.warning(view, "Error", "Please, select one folder to save the data.")
            return False

        # Visibility of progress bars
        view.progressLabel.show()
        view.progressBar.show()
        view.progressBar.setValue(0)
        view.error_occurred = False

        # If we are band segmenting, include the broadband as a new band, as we need it for the RP
        if view.main_window.controller.preproc_config['band_segmentation']:
            bands = view.main_window.controller.preproc_config['selected_bands']
            bands.insert(0,{
                "name": "broadband",
                "min": view.main_window.controller.preproc_config['broadband_min'],
                "max": view.main_window.controller.preproc_config['broadband_max']
            })
            view.main_window.controller.preproc_config['selected_bands'] = bands

        # Get configuration data, with error handling
        try:
            files = view.main_window.controller.files_config
            preprocessing = view.main_window.controller.preproc_config
            segmentation = view.main_window.controller.segmentation_config
            parameters = view.main_window.controller.parameters_config
        except AttributeError as e:
            QtWidgets.QMessageBox.critical(view, "Error",
                                           f"Unable to obtain the data from the main window: {e}")
            return

        # Create a settings dictionary grouping all configurations
        view.controller.settings_dic = {
            "files": files,
            "preprocessing": preprocessing,
            "segmentation": segmentation,
            "parameters": parameters
        }
        # Save the settings dict
        if view.settingsCBox.isChecked():
            view.controller.save_settings_to_json(view.controller.settings_dic)

        # Run the pipeline
        error_found = run_pipeline(view.controller, view.controller.settings_dic)

        # If success change the button text to "Close"
        if not error_found:
            view.main_window.nextButton.setText('Close')
            # Set the pipeline as completed, to avoid computing it again and closing the app
            view.controller.pipeline_completed = True

        return False # Prevent closing the app immediately

    # Otherwise, if the pipeline was already completed, return True to close the app
    else:
        return True