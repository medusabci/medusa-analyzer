import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PyQt5.QtGui import QIcon
from segmentation_widget import SegmentationWidget
from parameter_widget import ParameterWidget
import gui_utils as gu

class AnalyzerMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        theme_colors = gu.get_theme_colors(theme='dark')
        # self.set_theme()
        self.setWindowTitle('MEDUSA Analyzer')
        self.setGeometry(100, 100, 500, 200)

        self.setWindowIcon(QIcon('media/MDS_icon.png'))

        # Create QStackedWidget
        self.stacked_widget = QStackedWidget()

        # Stacked widgets
        self.segment_widget = SegmentationWidget()
        self.param_widget = ParameterWidget()
        self.stacked_widget.addWidget(self.segment_widget)  # Index 0
        self.stacked_widget.addWidget(self.param_widget)    # Index 1


        # Stacked widget as CentralWidget
        self.setCentralWidget(self.stacked_widget)

    def segmentation_view(self):
        self.stacked_widget.setCurrentIndex(0)

    def param_view(self):
        self.stacked_widget.setCurrentIndex(1)

    def set_theme(self):
        self.theme_colors = gu.get_theme_colors('dark')
        gu.set_css_and_theme(self, self.theme_colors)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = AnalyzerMainWindow()
    main_window.show()
    sys.exit(app.exec_())