# group_definition/view.py
from PyQt6 import QtWidgets, QtCore

class GroupDefinitionWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        # Título y descripción
        title = QtWidgets.QLabel("Define Experimental Groups")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.num_groups_spin = QtWidgets.QSpinBox()
        self.num_groups_spin.setRange(1, 10)
        self.generate_btn = QtWidgets.QPushButton("Generate Table")
        layout.addWidget(self.num_groups_spin)
        layout.addWidget(self.generate_btn)

        self.table = QtWidgets.QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Group Name", "Color"])
        layout.addWidget(self.table)

        self.back_button = QtWidgets.QPushButton("◀ Back")
        self.next_button = QtWidgets.QPushButton("Next ▶")
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(self.back_button)
        btn_layout.addWidget(self.next_button)
        layout.addLayout(btn_layout)
