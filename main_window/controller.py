from .ui import MainWindow
from PySide6.QtWidgets import QFrame
import numpy as np

class MainWindowController:
    def __init__(self):
        self.view = MainWindow()

    def set_progressbar(self):
        """
        Automatically creates the progress bar based on the number of steps in the stacked widget. It also activate the
        "Progress" label.
        """
        # Get current index and total steps of the selected experiment
        total_steps = self.view.stackedWidget.count()

        # Create the basis of the current progress bar
        layout = self.view.widget.layout()  # get the layout from the widget where the progress bar is located
        label_index = layout.indexOf(self.view.label)  # find the position of the label
        for n_step in range(total_steps):
            frame = QFrame()
            frame.setFixedWidth(25)                  # fixed width
            frame.setObjectName(f"frame_{n_step+1}")
            layout.insertWidget(label_index, frame)  # insert before the label

        # Set the label as visible
        self.progressLabel.setVisible(True)

        # Call update progressbar to paint the initial state
        self.update_progressbar()


    def update_progressbar(self):
        """
        Updates the progress bar according to the current index
        """
        # Get current index and total steps of the selected experiment
        idx = self.view.stackedWidget.currentIndex()
        total_steps = self.view.stackedWidget.count()

        # Update the label content
        self.view.progressLabel.setText(f"Step {idx + 1} of {total_steps}: {self.view.step_names[idx]}")
        # Paint the progress bar
        colors = self.interpolate_colors((106, 13, 173), (235, 64, 122), total_steps) # Get the color palette for the progress bar
        for n_step in range(total_steps):
            frame = self.view.widget.findChild(QFrame, f"frame_{n_step}")
            if n_step <= idx:
                frame.setStyleSheet(f"background-color: {colors[n_step]};")
            else:
                frame.setStyleSheet("background-color: lightgray;")


    def interpolate_colors(self, color1: tuple, color2: tuple, n: int):
        """
        Return a list of n colors interpolated between color1 and color2.
        Colors are RGB tuples (0–255).
        """
        c1 = np.array(color1)
        c2 = np.array(color2)

        colors = [
            tuple(((c1 + (c2 - c1) * i / (n - 1))).astype(int))
            for i in range(n)
        ]
        return colors
