import sys
from PySide6.QtWidgets import QApplication
from main_window.controller import MainWindowController
from main_window.view import MainWindow

def main():
        app = QApplication(sys.argv)
        ui = MainWindow()
        controller = MainWindowController(ui)
        ui.show()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()