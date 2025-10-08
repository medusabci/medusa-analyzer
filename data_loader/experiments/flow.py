import json, importlib
from PySide6.QtCore import QRunnable, Slot, QThreadPool, QObject, Signal
import time


class Worker(QRunnable):
    """Worker thread."""
    def __init__(self, view, fn):
        super().__init__()
        self.view = view
        self.fn = fn

    @Slot()
    def run(self):
        """Your long-running job goes in this method."""
        print("Thread start")
        self.fn(self.view)
        # time.sleep(5)
        print("Thread complete")
        self.view.main_window.controller.spinner.hide()
        print("Spinner off")



def on_next_click(view):
    """
    Handles the event when the "Next" button is clicked. It loads the selected experiment configuration
    """
    view.main_window.controller.spinner.show()

    threadpool = QThreadPool()
    worker = Worker(view, _on_next_click_aux)
    threadpool.start(worker)

    # # Update total steps and progress bar in the main window
    # view.main_window.nextButton.setDisabled(True)
    # # Deactivate Next button
    # view.main_window.controller.set_progressbar()



    return False


def _on_next_click_aux(view):
    # Get selected experiment
    checked_button = view.button_group.checkedButton()
    experiment_id = checked_button.property("experiment_id")

    # Read the corresponding config file
    with open(experiment_id + "/config.json", "r") as f:
        experiment_data = json.load(f)
        view.controller.experiment = experiment_data

    view.main_window.total_steps = len(view.controller.experiment['pipeline'])

    # Load the widgets, instantiate their controllers and add them to the stackedWidget
    for idx, widget_info in enumerate(view.controller.experiment['pipeline']):
        # Take the path
        widget_path = widget_info['path'].replace('/', '.')  # use dots instead of slashes

        # Import the view
        ui_module = importlib.import_module(f"{widget_path}.view")
        # Import the controller
        ctrl_module = importlib.import_module(f"{widget_path}.controller")

        # Get the classes from the modules
        widget_class = getattr(ui_module, widget_info['widget'])
        widget_controller_class = getattr(ctrl_module, widget_info['controller'])

        # Instantiate the widget
        widget = widget_class(view.main_window)
        # Instantiate the controller, passing the widget and the main window
        widget_controller_class(widget)

        # Optionally, add the widget to a stackedWidget
        view.main_window.stackedWidget.insertWidget(idx + 1, widget)

    # Store the experiment id
    view.main_window.selected_experiment = experiment_id
