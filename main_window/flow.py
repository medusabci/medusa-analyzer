def on_next_click(controller):
    """
        Controls the next (and finish) button behaviour
    """
    # Index of the current widget
    idx = controller.view.stackedWidget.currentIndex() # idx is the index of the previous widget

    # Call the specific on_next_clicked function of the current widget
    current_widget = controller.view.stackedWidget.widget(idx)
    widget_module = current_widget.__module__.rsplit('.', 1)[0]
    flow_module = __import__(widget_module + '.flow', fromlist=['on_next_click'])
    flow_module.on_next_click(current_widget)

    # Update the buttons and the stacked widget
    idx += 1 # Now is the index of the future widget
    controller.update_progressbar(idx)
    controller.view.backButton.setVisible(idx > 0)
    print('NEXT WIDGET INDEX:' + str(idx))
    if idx < controller.view.total_steps:
        controller.view.nextButton.setText("Next")
        controller.view.stackedWidget.setCurrentIndex(idx)
    elif idx == controller.view.total_steps:
        controller.view.nextButton.setText("Finish")
        controller.view.stackedWidget.setCurrentIndex(idx)
    else:
        controller.view.close()


def on_back_click(controller):
    """
        Controls the back button behaviour
    """
    idx = controller.view.stackedWidget.currentIndex() # idx is the index of the previous widget
    idx -= 1 # Now is the index of the future widget
    controller.view.backButton.setVisible(idx > 0)
    controller.view.stackedWidget.setCurrentIndex(idx)
    controller.view.nextButton.setDisabled(False)
    controller.view.nextButton.setText("Finish" if idx == controller.view.total_steps - 1 else "Next")
    controller.update_progressbar(idx)
    print(idx)

