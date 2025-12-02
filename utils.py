from PySide6 import QtWidgets,  QtCore

class LoadingDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, total_steps=5):
        super().__init__(parent)

        # Dialog box with no borders nor buttons, and always on top
        self.setWindowFlags(
            QtCore.Qt.Dialog |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )
        # Blocks interaction with the parent window
        self.setModal(True)
        # Transparent background
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.total_steps = total_steps

        # --- Style ---
        container = QtWidgets.QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(80, 80, 80, 220);
                border-radius: 8px;
            }
            QLabel { 
                color: white; 
                font-size: 14px;
                font-weight: bold;
                background: transparent; 
            }
            QProgressBar {
                border: 1px solid #888;
                border-radius: 5px;
                text-align: center;
                height: 16px;
            }
            QProgressBar::chunk {
                background-color: #b3b3b3;
                border-radius: 5px;
            }
        """)
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        # Text and progress bar
        self.label = QtWidgets.QLabel("Loading...", alignment=QtCore.Qt.AlignCenter)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        # Layout
        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)
        # Final widget
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.addWidget(container)

        # Center in the parent
        self.set_window_position(parent)

    def set_window_position(self, parent):
        if parent:
            # Dialog size
            dialog_width, dialog_height = 300, 120

            # Parent center in global coordinates
            parent_center = parent.mapToGlobal(parent.rect().center())

            # Upper left coordinates of the dialog to center it
            x = parent_center.x() - dialog_width // 2
            y = parent_center.y() - dialog_height // 2

            self.setGeometry(x, y, dialog_width, dialog_height)


    def set_progress(self, step, parent=None):
        self.progress_bar.setValue(step)
        QtWidgets.QApplication.processEvents()  # Refresh the UI

        # Center in the parent
        self.set_window_position(parent)

    def finish(self):
        QtWidgets.QApplication.processEvents()
        self.accept()  # Close the dialog box