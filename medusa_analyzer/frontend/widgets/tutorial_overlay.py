"""Interactive tutorial overlay carousel for MEDUSA Analyzer interfaces.

This module provides a modal, multi-step onboarding and contextual guidance overlay
that attaches to a parent QWidget. It renders sequential instruction cards containing
text descriptions, key bullet points, and comparative visual cards (examples) shown
in a two-column layout, allowing guided walk-throughs across analysis stages and
configuration workflows.

Relevant Classes:
    - TutorialExample: Visual support card rendered within step layouts.
    - TutorialStep: Data schema encapsulating content for a single tutorial page.
    - TutorialOverlay: Main overlay widget managing navigation, responsive resizing, and callbacks.

Component Hierarchy:
    tutorial_overlay.py
    ├── TutorialExample
    │
    ├── TutorialStep
    │
    └── TutorialOverlay
        ├── start
        ├── resizeEvent
        ├── _next
        ├── _previous
        ├── _skip
        ├── _close_and_continue
        ├── _render_step
        ├── _example_card
        ├── _update_panel_width
        ├── _center_panel
        └── _clear_layout

MEDUSA Analyzer Dependencies:
    - None
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QLayout, QPushButton, QSizePolicy,
                               QVBoxLayout, QWidget)


@dataclass(frozen=True, slots=True)
class TutorialExample:
    """Represents an atomic visual example or case study card displayed within a tutorial step.

    Parameters
    ----------
    title : str
        Header label summarizing the example context.
    text : str
        Descriptive explanation or practical guidance text.
    tone : str, default="neutral"
        Semantic visual variant applied to QSS styling (e.g., 'neutral', 'success', 'warning').
    """
    title: str
    text: str
    tone: str = "neutral"


@dataclass(frozen=True, slots=True)
class TutorialStep:
    """Data specification for an individual page within the tutorial carousel.

    Parameters
    ----------
    title : str
        Primary heading displayed at the top of the step card.
    body : str
        Main body paragraph describing the stage or operation.
    bullets : tuple[str, ...], default=()
        Ordered bullet points highlighting keypoints.
    examples : tuple[TutorialExample, ...], default=()
        Collection of visual example cards rendered in a dual-column grid at the bottom.
    """
    title: str
    body: str
    bullets: tuple[str, ...] = ()
    examples: tuple[TutorialExample, ...] = ()


class TutorialOverlay(QFrame):
    """Modal overlay carousel guiding users through multi-step operational flows."""

    completed = Signal()
    skipped = Signal()

    def __init__(self, parent: QWidget, title: str, steps: tuple[TutorialStep, ...]):
        """Initializes the overlay container, visual structure, and controls.

        Parameters
        ----------
        parent : QWidget
            Parent widget over which the overlay is positioned and resized.
        title : str
            Persistent tutorial series title displayed in the header.
        steps : tuple[TutorialStep, ...]
            Ordered sequence containing at least one step instance.
        """
        super().__init__(parent)
        if not steps:
            raise ValueError("TutorialOverlay requires at least one step.")

        self.title = title
        self.steps = steps
        self.current_index = 0
        self._after_close: Callable[[], None] | None = None

        self.setObjectName("tutorialOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.hide()

        self.panel = QFrame(self)
        self.panel.setObjectName("tutorialPanel")
        self.panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(30, 26, 30, 26)
        panel_layout.setSpacing(16)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(12)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("tutorialTitle")
        self.step_counter = QLabel("")
        self.step_counter.setObjectName("tutorialCounter")
        header.addWidget(self.title_label)
        header.addStretch()
        header.addWidget(self.step_counter)

        self.step_title = QLabel("")
        self.step_title.setObjectName("tutorialStepTitle")
        self.step_title.setWordWrap(True)

        self.body = QLabel("")
        self.body.setObjectName("tutorialBody")
        self.body.setWordWrap(True)

        self.bullets_container = QWidget()
        self.bullets_layout = QVBoxLayout(self.bullets_container)
        self.bullets_layout.setContentsMargins(0, 0, 0, 0)
        self.bullets_layout.setSpacing(8)

        self.examples_container = QWidget()
        self.examples_layout = QGridLayout(self.examples_container)
        self.examples_layout.setContentsMargins(0, 0, 0, 0)
        self.examples_layout.setHorizontalSpacing(10)
        self.examples_layout.setVerticalSpacing(10)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 6, 0, 0)
        actions.setSpacing(10)
        self.skip_button = QPushButton("Skip")
        self.skip_button.setProperty("variant", "ghost")
        self.skip_button.clicked.connect(self._skip)
        self.back_button = QPushButton("Back")
        self.back_button.setProperty("variant", "secondary")
        self.back_button.clicked.connect(self._previous)
        self.next_button = QPushButton("Next")
        self.next_button.setProperty("variant", "primary")
        self.next_button.clicked.connect(self._next)
        actions.addWidget(self.skip_button)
        actions.addStretch()
        actions.addWidget(self.back_button)
        actions.addWidget(self.next_button)

        panel_layout.addLayout(header)
        panel_layout.addWidget(self.step_title)
        panel_layout.addWidget(self.body)
        panel_layout.addWidget(self.bullets_container)
        panel_layout.addWidget(self.examples_container)
        panel_layout.addLayout(actions)

        self._render_step()

    def start(self, after_close: Callable[[], None] | None = None) -> None:
        """Opens the tutorial overlay, setting the navigation to the first step and adjusts geometry
        to the parent widget.

        Parameters
        ----------
        after_close : Callable[[], None] | None, optional
            Callback executed immediately after the overlay finishes or is dismissed.
        """
        self._after_close = after_close
        self.current_index = 0
        self._render_step()
        self.setGeometry(self.parentWidget().rect())
        self._update_panel_width()
        self._center_panel()
        self.raise_()
        self.show()

    def resizeEvent(self, event: QResizeEvent):
        """Adapts overlay geometry and repositions the central panel upon parent resize events."""
        if self.parentWidget():
            self.setGeometry(self.parentWidget().rect())
            self._update_panel_width()
            self._center_panel()
        super().resizeEvent(event)


    def _next(self) -> None:
        """Advances to the subsequent step, or concludes the tutorial on the final step."""
        if self.current_index < len(self.steps) - 1:
            self.current_index += 1
            self._render_step()
            return
        self.completed.emit()
        self._close_and_continue()


    def _previous(self) -> None:
        """Returns to the previous step in the sequence."""
        if self.current_index <= 0:
            return
        self.current_index -= 1
        self._render_step()


    def _skip(self) -> None:
        """Emits the skipped signal and closes the tutorial overlay."""
        self.skipped.emit()
        self._close_and_continue()


    def _close_and_continue(self) -> None:
        """Hides the overlay and triggers the registered completion callback."""
        callback = self._after_close
        self._after_close = None
        self.hide()
        if callback is not None:
            callback()


    def _render_step(self) -> None:
        """Refreshes counter labels, navigation buttons, and dynamic content layouts for the active step."""
        step = self.steps[self.current_index]
        self.step_counter.setText(f"{self.current_index + 1} / {len(self.steps)}")
        self.step_title.setText(step.title)
        self.body.setText(step.body)
        self.back_button.setEnabled(self.current_index > 0)
        self.next_button.setText("Start" if self.current_index == len(self.steps) - 1 else "Next")

        self._clear_layout(self.bullets_layout)
        for bullet in step.bullets:
            label = QLabel(f"- {bullet}")
            label.setObjectName("tutorialBullet")
            label.setWordWrap(True)
            self.bullets_layout.addWidget(label)

        self._clear_layout(self.examples_layout)
        for index, example in enumerate(step.examples):
            self.examples_layout.addWidget(self._example_card(example), index // 2, index % 2)
        self.examples_container.setVisible(bool(step.examples))


    def _example_card(self, example: TutorialExample) -> QFrame:
        """Constructs an individual visual card for an example item."""
        card = QFrame()
        card.setProperty("role", "tutorial-example")
        card.setProperty("tone", example.tone)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title = QLabel(example.title)
        title.setObjectName("tutorialExampleTitle")
        text = QLabel(example.text)
        text.setObjectName("tutorialExampleText")
        text.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(text)
        return card


    def _update_panel_width(self) -> None:
        """Recalculates and bounds the width of the central panel against available parent space."""
        parent = self.parentWidget()
        if not parent:
            return
        available_width = max(420, parent.width() - 96)
        self.panel.setFixedWidth(min(860, available_width))
        self.panel.adjustSize()


    def _center_panel(self) -> None:
        """Translates the central panel to the horizontal and vertical center of the available parent space."""
        left = max(0, (self.width() - self.panel.width()) // 2)
        top = max(0, (self.height() - self.panel.height()) // 2)
        self.panel.move(left, top)


    def _clear_layout(self, layout: QLayout) -> None:
        """Recursively removes and schedules destruction of all child widgets inside a layout."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
