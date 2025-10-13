import importlib
from PySide6 import QtWidgets

def on_next_click(controller):
    """
    Controla el botón Next/Plot. Llama al flow del widget actual.
    """
    idx = controller.view.stackedWidget.currentIndex()
    current_widget = controller.view.stackedWidget.widget(idx)
    module_name = current_widget.__module__.rsplit('.', 1)[0]  # p.ej. plots_and_stats.initial_configuration
    flow_module_name = f"{module_name}.flow"

    try:
        flow_module = importlib.import_module(flow_module_name)
    except ModuleNotFoundError:
        print(f"[FLOW] No flow module found for {module_name}")
        return

    # Llamamos al validador del widget actual (función definida en su flow.py)
    if hasattr(flow_module, "on_next_click"):
        can_continue, next_data = flow_module.on_next_click(current_widget)
        if not can_continue:
            return  # No pasar al siguiente paso si no está validado
    else:
        next_data = None

    # Avanzamos al siguiente widget
    idx += 1
    if idx < controller.view.stackedWidget.count():
        controller.view.stackedWidget.setCurrentIndex(idx)
        controller.view.backButton.setVisible(True)
        controller.view.nextButton.setText("Next")
    else:
        # Si no hay más widgets, puedes cerrarlo o lanzar el plot
        QtWidgets.QMessageBox.information(controller.view, "End", "All steps completed.")
        controller.view.close()


def on_back_click(controller):
    """
    Controla el botón Back. Simplemente retrocede.
    """
    idx = controller.view.stackedWidget.currentIndex()
    if idx > 0:
        controller.view.stackedWidget.setCurrentIndex(idx - 1)
        controller.view.nextButton.setText("Next")
        controller.view.backButton.setVisible(idx - 1 > 0)
