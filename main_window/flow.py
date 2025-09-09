def on_next_click(controller):
    """
        Controls the next (and finish) button behaviour
    """
    # Index of the current widget
    idx = controller.view.stackedWidget.currentIndex()

    # Call the specific on_next_clicked function of the current widget
    current_widget = controller.view.stackedWidget.widget(idx)
    widget_module = current_widget.__module__.rsplit('.', 1)[0]
    flow_module = __import__(widget_module + '.flow', fromlist=['on_next_click'])
    flow_module.on_next_click(current_widget)

    # Update the buttons and the stacked widget
    controller.update_progressbar()
    controller.view.nextButton.setText("Finish" if idx == controller.view.total_steps - 1 else "Next")
    controller.view.backButton.setVisible(idx + 1 > 0)
    if idx < controller.view.total_steps:
        controller.view.stackedWidget.setCurrentIndex(idx + 1)
    else:
        controller.view.close()


def on_back_click(controller):
    """
        Controls the back button behaviour
    """
    idx = controller.view.stackedWidget.currentIndex()
    controller.view.backButton.setVisible(idx > 0)
    if idx > 0:
        controller.view.stackedWidget.setCurrentIndex(idx - 1)
    controller.view.nextButton.setDisabled(False)
    controller.view.backButton.setVisible(idx - 1 > 0)
    controller.view.nextButton.setText("Finish" if idx == controller.view.total_steps - 1 else "Next")
    idx = controller.view.stackedWidget.currentIndex()
    controller.update_progressbar()
    print(idx)

