import importlib
from PySide6 import QtWidgets

def on_next_click(controller):
    """
    Controls the Next/Plot button. Calls the flow of the current widget.
    """

    # Index of the current widget
    idx = controller.view.stackedWidget.currentIndex()

    # Call the specific on_next_clicked function of the previous widget
    current_widget = controller.view.stackedWidget.widget(idx)
    module_name = current_widget.__module__.rsplit('.', 1)[0]  # e.g. plots_stats.config
    flow_module_name = f"{module_name}.flow"
    flow_module = importlib.import_module(flow_module_name)
    next_validation = flow_module.on_next_click(current_widget)
    if next_validation is False:
        return False

    idx += 1 # Now is the index of the next widget

    # Update the buttons, if going to the next widget, set text to "Next"
    if idx < controller.view.stackedWidget.count():
        controller.view.stackedWidget.setCurrentIndex(idx)
        controller.view.backButton.setVisible(True)
        controller.view.nextButton.setText("Next")
    # If going to the last widget
    elif idx == controller.view.stackedWidget.count():
        controller.view.nextButton.setText("Close")
    # If there are no more widgets, you can either close it or launch the plot.
    else:
        QtWidgets.QMessageBox.information(controller.view, "End", "All steps completed.")
        controller.view.close()


def on_back_click(controller):
    """
    Controls the Back button. Simply goes back.
    """
    idx = controller.view.stackedWidget.currentIndex()
    if idx > 0:
        controller.view.stackedWidget.setCurrentIndex(idx - 1)
        controller.view.nextButton.setText("Next")
        controller.view.backButton.setVisible(idx - 1 > 0)
