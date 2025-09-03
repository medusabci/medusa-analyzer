from PySide6.QtWidgets import QFrame
from PySide6.QtWidgets import QApplication
from main_window.ui import MainWindow
from data_loader.controller import DataLoaderController
from main_window.flow import go_next, go_back
import numpy as np


class MainWindowController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self

        self.view.nextButton.clicked.connect(lambda: go_next(self))
        self.view.backButton.clicked.connect(lambda: go_back(self))
        self.data_loader_controller = DataLoaderController(self.view.data_loader, self)


    def set_progressbar(self):
        """
        Automatically creates the progress bar based on the number of steps in the stacked widget. It also activate the
        "Progress" label.
        """

        # Create the basis of the current progress bar
        layout = self.view.widget.layout()  # get the layout from the widget where the progress bar is located
        label_index = layout.indexOf(self.view.progressLabel)  # find the position of the label
        for n_step in reversed(range(self.view.total_steps)):
            frame = QFrame()
            frame.setFixedWidth(25)                  # fixed width
            frame.setObjectName(f"frame_{n_step}")
            layout.insertWidget(label_index, frame)  # insert before the label

        # Set the label as visible
        self.view.progressLabel.setVisible(True)

        # Call update progressbar to paint the initial state
        self.update_progressbar()


    def update_progressbar(self):
        """
        Updates the progress bar according to the current index
        """
        # Get current index and total steps of the selected experiment
        idx = self.view.stackedWidget.currentIndex()

        # Update the label content
        self.view.progressLabel.setText(f"Step {idx + 1} of {self.view.total_steps}: "
                                        f"{self.view.experiment['pipeline'][0]['step']}")
        # Paint the progress bar
        colors = self.interpolate_colors_hex((106, 13, 173), (235, 64, 122), self.view.total_steps) # Get the color palette for the progress bar
        for n_step in range(self.view.total_steps):
            frame = self.view.widget.findChild(QFrame, f"frame_{n_step}")
            if n_step <= idx:
                frame.setStyleSheet(f"background-color: {colors[n_step]};")
            else:
                frame.setStyleSheet("background-color: lightgray;")


    def interpolate_colors_hex(self, color1, color2, n):
        """
        Return n colors between color1 and color2 as hex strings (#RRGGBB).
        color1, color2: RGB tuples (0-255)
        """
        c1 = np.array(color1)
        c2 = np.array(color2)

        colors_hex = []
        for i in range(n):
            rgb = ((c1 + (c2 - c1) * i / (n - 1)).astype(int))
            colors_hex.append("#{0:02x}{1:02x}{2:02x}".format(*rgb))
        return colors_hex


# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     ui = MainWindow()
#     controller = MainWindowController(ui)
#     ui.show()
#     sys.exit(app.exec())