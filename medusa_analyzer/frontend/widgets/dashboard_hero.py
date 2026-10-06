"""Dashboard Hero Banner Component for MEDUSA Analyzer.

This module provides the `DashboardHero` widget, which serves as the primary visual
header for the dashboard view. It displays the framework branding, application title,
subtitle, and descriptive feature chips, with responsive adaptations based on widget width.

Relevant Classes and Functions:
    - DashboardHero: Custom QFrame that renders the information and handles dynamic layout
     adjustments for responsive design.

MEDUSA Analyzer Dependencies:
    - None
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout


class DashboardHero(QFrame):
    """Initializes the DashboardHero widget and configures its layout.

    Constructs the widget hierarchy, applying container styles, branding labels
    (eyebrow, title, and subtitle), and an inline horizontal list of feature chips.
    """

    def __init__(self):
        super().__init__()
        self.setObjectName("dashboardHero")
        self.setMinimumHeight(224)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True) # esto es para que el fondo se pinte
        # bien a partir del QSS

        root = QVBoxLayout(self)
        root.setContentsMargins(42, 32, 42, 32)
        root.setSpacing(0)

        eyebrow = QLabel("MEDUSA BCI FRAMEWORK") # etiqueta pequeña superior
        eyebrow.setObjectName("dashboardEyebrow")

        title = QLabel("Medusa Analyzer") # título principal
        title.setObjectName("dashboardHeroTitle")
        title.setWordWrap(True)

        subtitle = QLabel("Create reproducible analysis pipelines for biomedical signals, "
                          "from data loading to final report.") # subtítulo
        subtitle.setObjectName("dashboardHeroSubtitle")
        subtitle.setWordWrap(True)

        root.addWidget(eyebrow)
        root.addSpacing(12)
        root.addWidget(title)
        root.addSpacing(8)
        root.addWidget(subtitle)
        root.addSpacing(22)

        self.chips = QHBoxLayout() # creamos fila horizontal para las etiquetas pequeñas
        self.chips.setSpacing(9)

        # Definimos dos chips
        for text, tone in (("Guided pipelines", "burgundy"), ("BIDS compatible", "teal")):
            chip = QLabel(text)
            chip.setObjectName("heroChip")
            chip.setProperty("tone", tone)
            self.chips.addWidget(chip)

        self.chips.addStretch() # stretch para empujar las chips a la izquierda
        root.addLayout(self.chips) # metemos la fila de chips en el hero

    def resizeEvent(self, event) -> None:
        """Handles responsive layout and style updates when the widget is resized.

        Dynamically updates content margins and triggers stylesheet re-polishing when the
        width falls below 620 px. Switches the feature chip container between horizontal
        and vertical arrangements when the width falls below 310 px.
        """
        compact = self.width() < 620
        stacked_chips = self.width() < 310

        if self.property("compact") != compact:
            self.setProperty("compact", compact)
            self.style().unpolish(self)
            self.style().polish(self)

            margins = (24, 26, 24, 27) if compact else (42, 32, 42, 32)
            self.layout().setContentsMargins(*margins)

        direction = (QHBoxLayout.Direction.TopToBottom if stacked_chips else QHBoxLayout.Direction.LeftToRight)

        if self.chips.direction() != direction:
            self.chips.setDirection(direction)
            self.chips.setSpacing(7 if stacked_chips else 9)

        super().resizeEvent(event)