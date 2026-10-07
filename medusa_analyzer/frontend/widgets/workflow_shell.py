"""Wizard-style workflow orchestrator for MEDUSA Analyzer experiment execution.

This module provides the main container widget responsible for hosting and coordinating
multi-step experiment flows. It renders persistent title headers, stage trackers,
action controls, and handles dynamic transitions across distinct stages.

Note:
    Step widgets and configurations are instantiated via `create_experiment_page()`.
    WorkflowShell hosts these views, synchronizes stepper states, and emits routing signals
    to allow the application shell to navigate back to the main view.

Relevant Classes:
    - WorkflowShell: Orchestrator managing dynamic page stacks, progress tracking, and validation guards for the
    experiments workflows.

Component Hierarchy:
    workflow_shell.py
    └── WorkflowShell (QWidget stage container and workflow coordinator)
        ├── _go_next
        ├── _go_back
        ├── _activate_current_step
        ├── _run_before_next
        ├── _current_step_can_continue
        ├── _visible_step_indices
        └── _refresh_navigation

MEDUSA Analyzer Dependencies:
    - medusa_analyzer.frontend.navigator.Navigator: Controls low-level page switching and index indexing inside the
    underlying QStackedWidget.
    - medusa_analyzer.frontend.widgets.progress_overlay.ProgressOverlay: Displays a modal loading overlay during
    computationally intensive step activations.
    - medusa_analyzer.frontend.widgets.step_progress_bar.StepProgressBar: Visual indicator rendering stage titles
     and reflecting completion, active, or locked states.
"""


from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout,
    QWidget)
from medusa_analyzer.frontend.navigator import Navigator
from medusa_analyzer.frontend.widgets.progress_overlay import ProgressOverlay
from medusa_analyzer.frontend.widgets.step_progress_bar import StepProgressBar


class WorkflowShell(QWidget):
    """Wizard-style orchestrator widget coordinating step-by-step experiment workflows.

    Renders header descriptions, step indicators, view stacks, and dynamic action buttons
    (Back / Next / Run / Dashboard), ensuring steps are validated and transitions are handled properly."""

    dashboard_requested = Signal()

    # El constructor recibe exactamente lo que pasa create_experiment_page()
    def __init__(self, title: str, subtitle: str, steps: list[dict[str, Any]], state: dict[str, Any]):
        """Initializes the workflow layout, step stack, navigation controls, and overlay.

        Parameters
        ----------
        title : str
            Experiment or workflow primary header title.
        subtitle : str
            Descriptive explanatory text positioned beneath the title.
        steps : list[dict[str, Any]]
            Ordered sequence of step specification dictionaries containing identifiers,labels, and target widget
            instances.
        state : dict[str, Any]
            Shared mutable state dictionary tracking workflow settings and parameters established during execution.
        """
        super().__init__()
        self.title = title
        self.subtitle = subtitle
        self.steps = steps
        self.state = state

        # Layout principal
        root = QVBoxLayout(self)
        root.setContentsMargins(34, 22, 34, 28)
        root.setSpacing(16)

        top = QHBoxLayout()
        back_to_dashboard = QPushButton("Back to dashboard")
        back_to_dashboard.setProperty("variant", "ghost")
        back_to_dashboard.clicked.connect(self.dashboard_requested)
        context = QLabel(title.upper()) # Título pequeño de arriba
        context.setObjectName("eyebrow")
        top.addWidget(back_to_dashboard)
        top.addStretch()
        top.addWidget(context)
        root.addLayout(top)

        page_title = QLabel(title) # Título principal
        page_title.setObjectName("pageTitle")
        root.addWidget(page_title)
        if subtitle:
            page_subtitle = QLabel(subtitle) # Subtítulo
            page_subtitle.setObjectName("muted")
            page_subtitle.setWordWrap(True)
            root.addWidget(page_subtitle)

        self.stepper = StepProgressBar([step["title"] for step in steps]) # Barra con los títulos de los pasos
        root.addWidget(self.stepper)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(divider)

        self.stack = QStackedWidget() # StackWidget para los pasos del experimento. Se mete dentro del Widget grande (WorkflowShell).
        self.navigator = Navigator(self.stack) # El navegador nos permité movernos por los diferentes steps
        for step in steps:
            widget = step["widget"]
            self.navigator.add_page(widget)

            # IMPORTANTE: Algunos widgets pueden tener una señal llamada changed. Por ejemplo, un widget de carga de
            # archivo puede tener changed = Signal() y cuando el usuario carga un archivo, el widget hace
            # self.changed.emit(). Entonces WorkflowShell refresca para actualizar botones, barra de progreso, etc.

            changed_signal = getattr(widget, "changed", None)
            if changed_signal is not None:
                changed_signal.connect(self._refresh_navigation)
        root.addWidget(self.stack, 1)

        actions = QHBoxLayout()

        # Botón para volver al dashboard
        self.back_button = QPushButton("Back to dashboard")
        self.back_button.setProperty("variant", "ghost")
        self.back_button.clicked.connect(self._go_back) # cuando se pulsa el botón, se emite la señal dashboard_requested
        self.next_button = QPushButton("Next")
        self.next_button.setProperty("variant", "primary")
        self.next_button.clicked.connect(self._go_next)
        actions.addWidget(self.back_button)
        actions.addStretch()
        actions.addWidget(self.next_button)
        root.addLayout(actions)

        self.overlay = ProgressOverlay(self, show_log=False)

        self._activate_current_step()
        self._refresh_navigation()


    def _go_next(self) -> None:
        """Validates current step prerequisites, executes transition logic, and advances or completes the workflow."""
        if not self._current_step_can_continue():
            return
        if not self._run_before_next():
            self._refresh_navigation()
            return
        visible_steps = self._visible_step_indices()
        current = self.navigator.current_index()
        # Si estamos en el último paso, verificamos si el experimento está completado o no.
        if current == visible_steps[-1]:
            # Si está completado, podremos pulsar en finish y volver al dashboard
            if self.state.get("completion_status") == "completed":
                self.dashboard_requested.emit()
                return
            # Si no, ejecutamos el run_pipeline y el botón será 'Run' en vez de 'Finish'
            widget = self.navigator.current_widget()
            run_pipeline = getattr(widget, "run_pipeline", None)
            if callable(run_pipeline):
                run_pipeline()
                self._refresh_navigation()
                return
            return
        # Si no estamos en el último paso, avanza al siguiente y actualiza la interfaz.
        next_steps = [index for index in visible_steps if index > current]
        self.navigator.go_to(next_steps[0]) # Para realmente avanzar, usamos la función del navigator.
        self._activate_current_step()
        self._refresh_navigation()


    def _go_back(self) -> None:
        """Navigates to the preceding visible step, or emits dashboard return if at the origin."""
        previous_steps = [index for index in self._visible_step_indices() if index < self.navigator.current_index()]
        if not previous_steps:
            self.dashboard_requested.emit()
            return
        # Si no estamos en el primer paso, vamos al paso anterior
        previous_step = previous_steps[-1]
        self.navigator.go_to(previous_step)
        # Después, actualizamos el paso actual y los botones
        self._activate_current_step()
        self._refresh_navigation()


    def _activate_current_step(self) -> None:
        """Invokes the activation process on the current step widget, displaying an overlay if required."""
        current_index = self.navigator.current_index()
        step = self.steps[current_index] if 0 <= current_index < len(self.steps) else {}
        show_progress = step.get("show_progress_overlay", False)

        widget = self.navigator.current_widget()
        on_step_activated = getattr(widget, "on_step_activated", None)
        if not callable(on_step_activated):
            return

        if show_progress:
            self.overlay.start_process("Preparing data...")
            self.overlay.progress.setValue(10)
            QApplication.processEvents()
            try:
                on_step_activated()
                self.overlay.progress.setValue(100)
                QApplication.processEvents()
            finally:
                self.overlay.hide()
        else:
            on_step_activated()

    def _run_before_next(self) -> bool:
        """Executes the pre-transition action on the active step widget, verifying if transition is allowed (indicated
        by the pre-transition action)."""
        widget = self.navigator.current_widget()
        action: Any = getattr(widget, "before_next", None)
        if callable(action):
            return action() is not False
        return True


    def _current_step_can_continue(self) -> bool:
        """Queries the active step widget to determine whether forward navigation is permitted."""
        widget = self.navigator.current_widget()
        can_continue: Any = getattr(widget, "can_continue", None)
        if callable(can_continue):
            # NOTA: can_continue es un métoodo opcional que puede tener un widget de un step hacer una validación
            # específica"
            return bool(can_continue())
        return True


    def _visible_step_indices(self) -> list[int]:
        """Resolves step indices by filtering out skipped steps (skipped steps are defined in load_data_widget
        and stored in the workflow_skip_steps dictionary)."""
        skipped_steps = self.state.get("workflow_skip_steps")
        skipped_ids = {str(step_id) for step_id in skipped_steps} if isinstance(skipped_steps, (list, tuple, set)) else set()
        visible_indices = [index for index, step in enumerate(self.steps) if str(step.get("id")) not in skipped_ids]
        return visible_indices or [self.navigator.current_index()]


    def _refresh_navigation(self) -> None:
        """Synchronizes step bar markers, button titles, and button interactive states to the active step state."""
        visible_steps = self._visible_step_indices()
        current = self.navigator.current_index()
        if current not in visible_steps:
            next_steps = [index for index in visible_steps if index > current]
            self.navigator.go_to(next_steps[0] if next_steps else visible_steps[-1])
            current = self.navigator.current_index()

        current_visible_index = visible_steps.index(current)
        stepper_labels = [self.steps[index]["title"] for index in visible_steps]
        if self.stepper.labels != stepper_labels:
            self.stepper.labels = stepper_labels
        states = []
        for index in range(len(visible_steps)):
            if index < current_visible_index:
                states.append("completed")
            elif index == current_visible_index:
                states.append("active")
            else:
                states.append("locked")
        # Le pasa a la barra el estado de cada uno de los pasos para que pueda actualizarse
        self.stepper.set_states(states)
        self.back_button.setText("Back" if current_visible_index > 0 else "Dashboard")
        if current == visible_steps[-1]:
            current_widget = self.navigator.current_widget()
            if bool(getattr(current_widget, "pipeline_running", False)):
                self.next_button.setText("Running...")
            elif self.state.get("completion_status") == "completed":
                self.next_button.setText("Back to dashboard")
            else:
                self.next_button.setText("Run")
        else:
            self.next_button.setText("Next")

        self.next_button.setEnabled(self._current_step_can_continue())
