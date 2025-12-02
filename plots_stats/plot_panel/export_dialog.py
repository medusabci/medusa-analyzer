from PySide6.QtWidgets import (QFileDialog, QDialog, QFormLayout, QSpinBox, QCheckBox, QColorDialog,
                               QComboBox, QLabel, QDialogButtonBox, QWidget, QHBoxLayout, QPushButton)
from PySide6.QtGui import QColor

class ExportDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Export options")
        self.setModal(True)
        layout = QFormLayout(self)

        # --- Format ---
        self.format_combo = QComboBox()
        self.format_combo.addItems(["png", "jpg", "pdf", "svg"])
        layout.addRow(QLabel("Format:"), self.format_combo)

        # --- Width ---
        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 8000)
        self.width_spin.setValue(1200)
        layout.addRow(QLabel("Width (px):"), self.width_spin)

        # --- Height ---
        self.height_spin = QSpinBox()
        self.height_spin.setRange(100, 8000)
        self.height_spin.setValue(800)
        layout.addRow(QLabel("Height (px):"), self.height_spin)

        # --- DPI ---
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(50, 1200)
        self.dpi_spin.setValue(300)
        layout.addRow(QLabel("DPI:"), self.dpi_spin)

        # --- Transparent background ---
        self.transparent_chk = QCheckBox("Transparent background (if supported)")
        layout.addRow(self.transparent_chk)

        # --- Background color chooser ---
        color_layout = QHBoxLayout()
        self.color_button = QPushButton("Choose color")
        self.color_label = QLabel()
        self.color_label.setAutoFillBackground(True)
        self.bg_color = QColor("white")  # default background color
        self.update_color_label()

        self.color_button.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_button)
        color_layout.addWidget(self.color_label)
        layout.addRow(QLabel("Background color:"), color_layout)

        # --- OK / Cancel buttons ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_values(self):
        return {
            "format": self.format_combo.currentText(),
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "dpi": self.dpi_spin.value(),
            "transparent": self.transparent_chk.isChecked(),
            "bg_color": self.bg_color.name(),
        }

    def choose_color(self):
        color = QColorDialog.getColor(self.bg_color, self, "Select background color")
        if color.isValid():
            self.bg_color = color
            self.update_color_label()

    def update_color_label(self):
        """Updates the label background to show the selected color."""
        palette = self.color_label.palette()
        palette.setColor(self.color_label.backgroundRole(), self.bg_color)
        self.color_label.setAutoFillBackground(True)
        self.color_label.setPalette(palette)
        self.color_label.setText(self.bg_color.name().upper())