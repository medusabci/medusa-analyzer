from PySide6.QtWidgets import QFrame
import numpy as np


class MainWindowController:
    def __init__(self, ui):
        self.view = ui

        self.view.nextButton.clicked.connect(self.go_next)
        self.view.backButton.clicked.connect(self.go_back)
        # #
        # self.view.stackedWidget.currentChanged.connect(self.on_tab_changed)
        self.set_progressbar()


    def go_next(self):
        """
            Controls the next (and finish) button behaviour
        """
        idx = self.view.stackedWidget.currentIndex()
        self.view.nextButton.setText("Finish" if idx == self.total_steps - 1 else "Next")
        if idx < self.view.total_steps - 1:
            self.view.stackedWidget.setCurrentIndex(idx + 1)
            self.view.update_ui()
        else:
            self.view.close()


    def go_back(self):
        """
            Controls the back button behaviour
        """
        idx = self.view.stackedWidget.currentIndex()
        self.view.backButton.setVisible(idx > 0)
        if idx > 0:
            self.view.stackedWidget.setCurrentIndex(idx - 1)
            self.view.update_ui()


    def set_progressbar(self):
        """
        Automatically creates the progress bar based on the number of steps in the stacked widget. It also activate the
        "Progress" label.
        """
        # Get current index and total steps of the selected experiment
        self.total_steps = self.view.stackedWidget.count()

        # Create the basis of the current progress bar
        layout = self.view.widget.layout()  # get the layout from the widget where the progress bar is located
        label_index = layout.indexOf(self.view.progressLabel)  # find the position of the label
        for n_step in reversed(range(self.total_steps)):
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
        # self.view.progressLabel.setText(f"Step {idx + 1} of {self.total_steps}: {self.view.pipeline[idx]}")
        # Paint the progress bar
        colors = self.interpolate_colors_hex((106, 13, 173), (235, 64, 122), self.total_steps) # Get the color palette for the progress bar
        for n_step in range(self.total_steps):
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

#
# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     ui = MainWindow()
#     controller = MainWindowController(ui)
#     ui.show()
#     sys.exit(app.exec())