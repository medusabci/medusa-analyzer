def on_next_click(controller):
    """
    Controls the next (and finish) button behaviour
    """
    # Index of the current widget
    idx = controller.view.stackedWidget.currentIndex() # idx is the index of the previous widget

    # Call the specific on_next_clicked function of the previous widget
    current_widget = controller.view.stackedWidget.widget(idx)
    widget_module = current_widget.__module__.rsplit('.', 1)[0]
    flow_module = __import__(widget_module + '.flow', fromlist=['on_next_click'])
    flow_module.on_next_click(current_widget)

    idx += 1 # Now is the index of the next widget

    # Update the buttons, the progressbar, and the stacked widget
    controller.update_progressbar(idx)
    controller.view.stackedWidget.setCurrentIndex(idx)
    controller.view.backButton.setVisible(idx > 0)
    if idx < controller.view.total_steps:
        controller.view.nextButton.setText("Next")
    elif idx == controller.view.total_steps: # If going to the last widget
        controller.view.nextButton.setText("Finish")
    else: # If in the last widget and clicking "Finish"
        controller.view.close()


def on_back_click(controller):
    """
    Controls the back button behaviour
    """
    idx = controller.view.stackedWidget.currentIndex() # idx is the index of the previous widget
    idx -= 1 # Now is the index of the future widget

    # Update the buttons, the progressbar, and the stacked widget
    controller.update_progressbar(idx)
    controller.view.stackedWidget.setCurrentIndex(idx)
    controller.view.backButton.setVisible(idx > 0)
    controller.view.nextButton.setDisabled(False)
    controller.view.nextButton.setText("Finish" if idx == controller.view.total_steps - 1 else "Next")
