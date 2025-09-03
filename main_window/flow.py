def go_next(controller):
    """
        Controls the next (and finish) button behaviour
    """
    idx = controller.view.stackedWidget.currentIndex()
    controller.view.nextButton.setText("Finish" if idx == controller.view.total_steps - 1 else "Next")
    if idx < controller.view.total_steps - 1:
        controller.view.stackedWidget.setCurrentIndex(idx + 1)
    else:
        controller.view.close()


def go_back(controller):
    """
        Controls the back button behaviour
    """
    idx = controller.view.stackedWidget.currentIndex()
    controller.view.backButton.setVisible(idx > 0)
    if idx > 0:
        controller.view.stackedWidget.setCurrentIndex(idx - 1)