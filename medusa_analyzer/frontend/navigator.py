"""Page navigation controller for multi-step workflows in MEDUSA Analyzer.

This module provides the `Navigator` utility class, designed to wrap and streamline
navigation across pages within a `QStackedWidget` container. It encapsulates index
boundaries checking, dynamic view transitions, and step tracking for wizard-like
interfaces.

Relevant Classes and Functions:
    - Navigator: Controller wrapping a QStackedWidget to manage sequential and indexed page transitions.

Component Hierarchy:
    navigator.py
    └── Navigator
        ├── next
        ├── back
        ├── go_to
        ├── add_page
        ├── current_index
        ├── count
        └── current_widget


MEDUSA Analyzer Dependencies:
    - None
"""

from PySide6.QtWidgets import QStackedWidget, QWidget


class Navigator:
    """Controls sequential and indexed page switching within a QStackedWidget container."""
    def __init__(self, stack: QStackedWidget):
        """Initializes the Navigator instance providing a stacked widget.

        Parameters
        ----------
        stack : QStackedWidget
            The stacked widget container whose page transitions will be managed.
        """
        self.stack = stack # Recibe un stackedWidget y lo guarda


    def next(self) -> None:
        """Advances the view to the next sequential page in the stack."""
        self.go_to(self.current_index() + 1)


    def back(self) -> None:
        """Navigates the view back to the preceding page in the stack."""
        self.go_to(self.current_index() - 1)


    def go_to(self, index: int) -> None:
        """Transitions the view to the page at the specified index."""
        if not 0 <= index < self.count(): # comprueba que el índice exista
            raise ValueError(f"Step index out of range: {index}")
        self.stack.setCurrentIndex(index) # cambia el paso visible


    def add_page(self, page: QWidget) -> None:
        """Appends a new page widget to the end of the stack."""
        self.stack.addWidget(page)


    def current_index(self) -> int:
        """Returns the zero-based index of the currently active page."""
        return self.stack.currentIndex()


    def count(self) -> int:
        """Returns the total number of pages currently registered in the stack"""
        return self.stack.count()


    def current_widget(self) -> QWidget:
        """Returns the widget instance corresponding to the currently displayed page."""
        return self.stack.currentWidget()