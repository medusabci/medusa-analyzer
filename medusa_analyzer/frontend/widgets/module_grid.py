"""Responsive grid container for dashboard experiment cards in MEDUSA Analyzer dashboard.

This module provides the `ModuleGrid` widget, which arranges multiple `ExperimentCard`
instances into a multi-column responsive layout. It calculates column counts, card
widths, and dynamic minimum heights according to available container width.

Relevant Classes and Functions:
    - ModuleGrid: Responsive QWidget container managing grid flow and card dimensions.

MEDUSA Analyzer Dependencies:
    - medusa_analyzer.frontend.widgets.experiment_card.ExperimentCard: Visual card
      widget instances managed and arranged within the grid.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QWidget

from medusa_analyzer.frontend.widgets.experiment_card import ExperimentCard


class ModuleGrid(QWidget):
    """Responsive container displaying experiment cards in an adaptive grid layout.

    Calculates horizontal capacity, card sizing boundaries, and vertical footprint
    to dynamically rearrange cards as the parent container resizes.
    """

    # Constantes que controlan el layout
    CARD_MIN_WIDTH = 244
    CARD_MAX_WIDTH = 304
    CARD_COMPACT_WIDTH = 208
    CARD_HEIGHT = 344
    GAP = 22 # espacio vertical/horizontal entre tarjetas

    def __init__(self):
        """Initializes the ModuleGrid container, card list, and layout settings."""
        super().__init__()
        self.setObjectName("moduleGrid")
        self.cards: list[ExperimentCard] = []
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(self.GAP)
        self.grid.setVerticalSpacing(self.GAP)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)


    def add_card(self, card: ExperimentCard) -> None:
        """Appends an experiment card to the registry and triggers a layout reflow.

        Parameters
        ----------
        card : ExperimentCard
            The experiment card instance to insert into the grid.

        MEDUSA Analyzer Dependencies:
            - medusa_analyzer.frontend.widgets.experiment_card.ExperimentCard: The
              target card widget added to the internal collection.
        """
        self.cards.append(card)
        self._reflow() # recalcula la distribución completa


    def _reflow(self) -> None:
        """Reconstructs the grid layout, resizes cards, and updates container height.

        Empties the current grid arrangement without destroying card instances,
        recalculates card dimensions, positions items into the newly calculated
        rows and columns, and establishes the new required minimum height.
        """
        while self.grid.count():
            self.grid.takeAt(0) # vacía el layout, pero no destruye las tarjetas (siguen en self.cards)
        columns = self._column_count()  # calcula cuántas columnas a usar
        available = max(1, self.width()) # lee ancho disponible
        width_per_column = (available - self.GAP * (columns - 1)) // columns
        card_width = min(self.CARD_MAX_WIDTH, max(self.CARD_COMPACT_WIDTH, width_per_column)) # ancho final de las tarjetas
        for index, card in enumerate(self.cards):
            card.set_card_width(card_width)  # decimos a cada tarjeta qué ancho tener (métoodo de module_grid)
            self.grid.addWidget(card, index // columns, index % columns)
        rows = (len(self.cards) + columns - 1) // columns
        self.setMinimumHeight(rows * self.CARD_HEIGHT + max(0, rows - 1) * self.GAP)


    def _column_count(self) -> int:
        """Calculates the optimal number of grid columns for the current widget width."""
        if not self.cards:
            return 1
        available = max(1, self.width())  # ancho actual
        # calculamos cuántas tarjetas de ancho mínimo caben
        possible = max(1, (available + self.GAP) // (self.CARD_MIN_WIDTH + self.GAP))
        return min(len(self.cards), possible, 4)


    def resizeEvent(self, event) -> None:
        """Triggers grid reflow to update columns and card widths and positions upon resizing."""
        self._reflow()
        super().resizeEvent(event)
