from PySide6.QtWidgets import QFrame, QLabel
from PySide6 import QtCore, QtGui
from main_window.flow import on_next_click, on_back_click
import numpy as np

class LoadingSpinner(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Floating window with no borders
        self.setWindowFlags(
            QtCore.Qt.Dialog |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool )

        # Transparent background
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # Align center
        self.setAlignment(QtCore.Qt.AlignCenter)

        # Window size and style
        self.setFixedSize(120, 120)
        self.setStyleSheet("background-color: rgba(255, 255, 255, 180); border-radius: 10px;")

        # Load the GIF and start the animation
        self.movie = QtGui.QMovie("media/loading.gif")
        self.setMovie(self.movie)
        self.movie.start()


class MainWindowController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self

        # Buttons connections
        self.view.nextButton.clicked.connect(self.on_next_click_loading)
        self.view.backButton.clicked.connect(lambda: on_back_click(self))

        # Spinner for loading
        self.spinner = LoadingSpinner()
        self.spinner.hide()

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
        self.update_progressbar(1)


    def update_progressbar(self, idx):
        """
        Updates the progress bar according to the current index
        """

        if idx == 0:
            # Update the label content
            self.view.progressLabel.setVisible(False)
            for n_step in range(self.view.total_steps):
                frame = self.view.widget.findChild(QFrame, f"frame_{n_step}")
                frame.setVisible(False)
        else:
            # Update the label content
            self.view.progressLabel.setVisible(True)
            self.view.progressLabel.setText(f"Step {idx} of {self.view.total_steps}: "
                                            f"{self.view.stackedWidget.widget(0).controller.experiment['pipeline'][0]['step']}")
            # Paint the progress bar
            colors = self.interpolate_colors_hex((106, 13, 173), (235, 64, 122), self.view.total_steps) # Get the color palette for the progress bar
            for n_step in range(self.view.total_steps):
                frame = self.view.widget.findChild(QFrame, f"frame_{n_step}")
                frame.setVisible(True)
                if n_step <= idx-1:
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

    def on_next_click_loading(self):
        self.spinner.show()
        on_next_click(self)
        self.spinner.hide()