"""Route navigation manager for MEDUSA Analyzer interfaces.

This module provides the `Router` class, which handles string-based routing and view
switching on top of a `QStackedWidget`. It associates explicit route identifiers with
concrete widget instances and manages navigation transitions and error notifications.

While 'Navigator' manages the navigation within an experiment, 'Router' manages the
navigation between experiments and dashboard.

Relevant Classes and Functions:
    - Router: Controller mapping string route keys to QWidget views within a QStackedWidget.

MEDUSA Analyzer Dependencies:
    - None
"""

import logging

from PySide6.QtWidgets import QMessageBox, QStackedWidget, QWidget


logger = logging.getLogger(__name__)

# Controla qué página se ve dentro del QStackedWidget
class Router:
    """Manages string-keyed widget registration and display transitions within a QStackedWidget."""
    def __init__(self, stack: QStackedWidget):
        """Initializes the Router with a target stacked widget and an empty route registry.

        Parameters
        ----------
        stack : QStackedWidget
            The stacked widget container where registered pages are mounted.
        """
        self.stack = stack
        self.routes: dict[str, QWidget] = {}

    def register(self, route: str, page: QWidget) -> None:
        """Registers a view widget under a unique route identifier and mounts it into the stack.

        Parameters
        ----------
        route : str
            Unique string key identifying the destination view.
        page : QWidget
            Widget instance corresponding to the registered route.
        """
        self.routes[route] = page
        self.stack.addWidget(page) # Añadimos los widgets correspondientes al experimento, o el dashboard

    def navigate(self, route: str) -> None:
        """Transitions the display to the widget associated with the given route identifier.

        Parameters
        ----------
        route : str
            Identifier of the destination view to display. Displays an error dialog
            and logs a critical message if the route is not registered.
        """
        page = self.routes.get(route)
        if page is None:
            logger.error("Unknown route '%s'. Available routes: %s", route, sorted(self.routes))
            QMessageBox.critical(self.stack, "Navigation error", f"Unknown route: {route}")
            return
        self.stack.setCurrentWidget(page)
