"""Interactive experiment card component for MEDUSA Analyzer dashboard.

This module provides the visual and interactive card widget used in the dashboard
to display and launch analysis workflows and experiments. It encapsulates different
visual features: state badges, circular icon rendering, elevation hover animations,
and keyboard/mouse activation mechanisms.

Relevant Classes and Functions:
    - _render_circular_icon: Helper function to crop and antialias image icons into circles.
    - ExperimentCard: Interactive QWidget card container with elevation and focus handling.

MEDUSA Analyzer Dependencies:
    - None
"""

from pathlib import Path

from PySide6.QtCore import (Property, QEasingCurve, QEvent, QPropertyAnimation,
    QRectF, Qt, Signal)
from PySide6.QtGui import (QColor, QCursor, QKeyEvent, QMouseEvent, QPainter,
    QPainterPath, QPixmap)
from PySide6.QtWidgets import (QFrame, QGraphicsDropShadowEffect, QHBoxLayout,
    QLabel, QSizePolicy, QVBoxLayout, QWidget)


def _render_circular_icon(icon_path: Path, size: int = 106) -> QPixmap:
    """Loads and crops an image file into an antialiased circular QPixmap.

    Parameters
    ----------
    icon_path : Path
        Filesystem path pointing to the icon image.
    size : int, optional
        Target diameter in pixels for the circular output, by default 106.

    Returns
    -------
    QPixmap
        Rendered circular pixmap with an alpha-channel background.
    """
    pixmap = QPixmap(str(icon_path))
    crop_size = int(min(pixmap.width(), pixmap.height()) * 0.76)
    crop = pixmap.copy(
        (pixmap.width() - crop_size) // 2,
        (pixmap.height() - crop_size) // 2,
        crop_size,
        crop_size,
    )
    scaled = crop.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    clipped = QPixmap(size, size)
    clipped.fill(Qt.GlobalColor.transparent)

    painter = QPainter(clipped)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addEllipse(QRectF(0, 0, size, size))
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, scaled)
    painter.end()

    return clipped

# Clase para definir la tarjeta visual clicable que aparece en el dashboard para abrir un experimento.
class ExperimentCard(QWidget):
    """Interactive dashboard card representing an analysis experiment or workflow.

    Provides visual identification via cropped icon, title, description, and status
    badge. Supports hover elevation animations, keyboard navigation, and click signals.
    """

    clicked = Signal() # definimos una señal llamada clicked

    def __init__(self, title: str, subtitle: str, icon_path: Path | None, enabled: bool = True,
        status: str = "", accent: str = "burgundy"):
        """Initializes the ExperimentCard widget, subcomponents, and animations.

        Parameters
        ----------
        title : str
            Display name of the experiment.
        subtitle : str
            Brief descriptive summary of the workflow.
        icon_path : Path or None
            File path to the card's visual icon, or None to display fallback text.
        enabled : bool, optional
            Whether the card can be interacted with, by default True.
        status : str, optional
            Explicit status override (e.g., 'Beta', 'Updating'), by default "".
        accent : str, optional
            Color theme token used for styling properties, by default "burgundy".
        """
        super().__init__()
        self._hover_progress = 0.0 # variable que controla la animación de hover
        self._enabled = enabled # guarda si está habilitada
        self.setObjectName("moduleCardShell") # nombre del widget
        self.setProperty("role", "module-card-shell")
        self.setProperty("enabled", enabled)
        self.setProperty("accent", accent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus if enabled else Qt.FocusPolicy.NoFocus)
        # Hacemos que el cursor sea una mano si está habilitada (si no, cursor normal)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor))
        self.setAccessibleName(f"{title}. {subtitle.rstrip('.')}." + (f" {status}" if status else ""))
        self.setAccessibleDescription("Open this experiment workflow." if enabled else "This module is coming soon.")
        self.setToolTip(f"Open {title}" if enabled else f"{title} is coming soon") # tooltip de la tarjeta
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(304, 344) # tamaño fijo

        self.surface = QFrame(self) # panel visual de la tarjeta
        self.surface.setObjectName("moduleCard")
        self.surface.setProperty("role", "module-card")
        self.surface.setProperty("enabled", enabled)
        self.surface.setProperty("accent", accent)
        # Hacemos que surface ignore los eventos de ratón. Aquí los clicks no se quedan en el QFrame interno, sino que
        # llegan al ExperimentCard exterior, que es quien tiene mouseReleaseEvent().
        self.surface.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.shadow = QGraphicsDropShadowEffect(self.surface) # creamos una sombra para surface
        self.shadow.setBlurRadius(25)
        self.shadow.setOffset(0, 7)
        self.shadow.setColor(QColor(54, 30, 39, 36))
        self.surface.setGraphicsEffect(self.shadow) # aplicamos la sombra al panel

        root = QVBoxLayout(self.surface) # layout vertical dentro de surface
        root.setContentsMargins(30, 24, 30, 27)
        root.setSpacing(0)

        badge_row = QHBoxLayout()
        badge_row.addStretch()
        # Etiqueta del estado. Si estatus tiene texto, usa ese. Sino puede ser "Available" o "Coming soon"
        badge = QLabel(status or ("Available" if enabled else "Coming soon"))
        badge.setObjectName("moduleBadge")
        badge.setProperty("status", "ready" if enabled else "soon")
        badge_row.addWidget(badge)
        root.addLayout(badge_row)
        root.addSpacing(13)

        icon = QLabel()
        icon.setObjectName("moduleIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(126, 126)
        if icon_path is not None and icon_path.is_file():
            icon.setPixmap(_render_circular_icon(icon_path, size=106))
        else:
            icon.setText(title)
        root.addWidget(icon, alignment=Qt.AlignmentFlag.AlignHCenter)
        root.addSpacing(15)

        title_label = QLabel(title) # Título
        title_label.setObjectName("moduleTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title_label)
        root.addSpacing(9)

        accent_line = QFrame() # Línea decorativa debajo del título
        accent_line.setObjectName("moduleAccent")
        accent_line.setFixedSize(48, 3)
        root.addWidget(accent_line, alignment=Qt.AlignmentFlag.AlignHCenter)
        root.addSpacing(13)

        description = QLabel(subtitle) # Texto descriptivo a partir del subtítulo
        description.setObjectName("moduleDescription")
        description.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        description.setWordWrap(True)
        description.setFixedHeight(42)
        root.addWidget(description)
        root.addStretch()

        # Texto inferior de la tarjeta
        hint = QLabel("ENTER WORKFLOW" if enabled else "WORKFLOW LOCKED")
        hint.setObjectName("moduleHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(hint)

        # Creamos una animación sobre la propiedad del hover
        self.animation = QPropertyAnimation(self, b"hoverProgress", self)
        self.animation.setDuration(180)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._position_surface()


    def set_card_width(self, width: int) -> None:
        """Updates the fixed width of the card and recalculates inner surface geometry,
        for responsive adaptations.
        """
        self.setFixedWidth(width)
        self._position_surface()


    def get_hover_progress(self) -> float:
        """Returns the current progress value of the hover elevation animation."""
        return self._hover_progress


    def set_hover_progress(self, value: float) -> None:
        """Applies hover animation progress to surface position and drop-shadow parameters."""
        self._hover_progress = value
        self._position_surface()
        self.shadow.setBlurRadius(25 + 11 * value)
        self.shadow.setOffset(0, 7 - 2 * value)


    hoverProgress = Property(float, get_hover_progress, set_hover_progress)

    def _animate_to(self, target: float) -> None:
        """Transitions hover progress toward a target state and refreshes styles."""
        if not self._enabled: # si la tarjeta está deshabilitada, no anima.
            return
        self.animation.stop()
        self.animation.setStartValue(self._hover_progress)
        self.animation.setEndValue(target)
        self.animation.start()
        active = target > 0
        self.surface.setProperty("hovered", active)
        self._refresh_surface_style()


    def _position_surface(self) -> None:
        """Calculates and updates surface geometry based on current hover elevation."""
        lift = round(self._hover_progress * 4)
        self.surface.setGeometry(8, 10 - lift, max(0, self.width() - 16), 322)


    def _refresh_surface_style(self) -> None:
        """Forces Qt style recalculation on the inner surface widget."""
        self.surface.style().unpolish(self.surface)
        self.surface.style().polish(self.surface)


    def enterEvent(self, event: QEvent) -> None:
        """Triggers the forward hover elevation animation upon cursor entry."""
        self._animate_to(1.0)
        super().enterEvent(event)


    def leaveEvent(self, event: QEvent) -> None:
        """Triggers the reverse elevation animation when the cursor departs."""
        self._animate_to(0.0)
        super().leaveEvent(event)


    def focusInEvent(self, event) -> None:
        """Applies focused state styling when the card receives keyboard focus."""
        self.surface.setProperty("focused", True)
        self._refresh_surface_style()
        super().focusInEvent(event)


    def focusOutEvent(self, event) -> None:
        """Removes focused state styling when the card loses keyboard focus."""
        self.surface.setProperty("focused", False)
        self._refresh_surface_style()
        super().focusOutEvent(event)


    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Emits the clicked signal when the card is left-clicked while enabled."""
        if self._enabled and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit() # Emitimos señal de que se ha clicado en la tarjeta para que lo reciba el dashboard
        super().mouseReleaseEvent(event)


    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Emits the clicked signal upon Enter or Space key press while focused."""
        if self._enabled and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit() # Emitimos señal de que se ha clicado en la tarjeta para que lo reciba el dashboard
            event.accept()
            return
        super().keyPressEvent(event)


    def resizeEvent(self, event) -> None:
        """Recalculates inner surface positioning when the widget dimensions change."""
        self._position_surface()
        super().resizeEvent(event)
