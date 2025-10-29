import time, sys
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.text_area = QTextEdit("Hola\n")
        self.layout = QVBoxLayout()
        self.button = QPushButton("Start")
        self.layout.addWidget(self.text_area)
        self.layout.addWidget(self.button)

        central_widget = QWidget()
        central_widget.setLayout(self.layout)
        self.setCentralWidget(central_widget)

        self.button.clicked.connect(self.start)
        self.show()

    def on_log(self, msg):
        try:
            current_txt = self.text_area.toPlainText()
            new_txt = current_txt + '\n' + msg
            print(new_txt)
            self.text_area.setText(new_txt)
        except Exception as e:
            print(e)

    def start(self):
        self.worker = Worker()
        self.worker.log.connect(self.on_log)
        self.worker.start()


class Worker(QThread):

    log = Signal(str)

    def __init__(self):
        super().__init__()

    def run(self):
        for i in range(10):
            print(i)
            self.log.emit(str(i))
            time.sleep(1)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ui = MainWindow()
    ui.show()
    sys.exit(app.exec())