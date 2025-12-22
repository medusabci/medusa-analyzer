import sys
from PySide6.QtWidgets import QApplication
from converter.controller import MainConverterController
from converter.view import MainConverter

def main():
        app = QApplication(sys.argv)
        ui = MainConverter()
        controller = MainConverterController(ui)
        ui.show()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()