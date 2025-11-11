from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType

# Load UI class
ui_step_1 = loadUiType('experiment_template/step_1/view.ui')[0]

class Step1Widget(QtWidgets.QWidget, ui_step_1):
    shown = QtCore.Signal() # Signal to be emitted when the widget is shown

    def __init__(self, main_window):
        super().__init__()
        self.setupUi(self)
        self.main_window = main_window

        ### DATA LOADER HEADER ###

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.topContentWidget.setLayout(layout)

        self.description_label = QtWidgets.QLabel()
        self.description_label.setTextFormat(QtCore.Qt.RichText)
        self.description_label.setWordWrap(True)
        self.description_label.setAlignment(QtCore.Qt.AlignCenter)

        self.description_label.setText("""
            <div style="text-align:center; font-family:'Segoe UI', Arial;">
                <p style="font-size: 12pt; color:#444; margin:0 40px 10px 40px;">
                    Header of the widget.
                </p>

                <p style="font-size: 11pt; color:#666; margin:0 40px;">
                    Explanations <b style="color:#007acc;">explanations</b>, and <b>more</b> explanations.
                </p>
            </div>
        """)

        # Remove background
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Base, palette.color(QtGui.QPalette.Window))
        self.topContentWidget.setPalette(palette)
        self.topContentWidget.setFrameShape(QtWidgets.QFrame.NoFrame)

        layout.addWidget(self.description_label)


        ### ELEMENT CONFIGURATION ###

        # Set initial state
        for widget in [self.label1, self.label2, self.text1, self.text2]:
            widget.setVisible(False)

        # Set default values for something
        self.box1.setValue(1)
        self.box2.setValue(2)

        # Default values in a dict
        self.defaults = {
            "box1": self.box1.value(),
            "box2": self.box2.value(),
            "some_text1": self.text1.text(),
            "some_text2": self.text2.text()
        }

    def showEvent(self, event):
        super().showEvent(event)
        self.shown.emit() # Signal emission