from PySide6 import QtWidgets, QtCore
from PySide6.QtUiTools import loadUiType

ui_plots_init = loadUiType('plots_and_stats/initial_configuration/view.ui')[0]

class PlotStatsInitView(QtWidgets.QWidget, ui_plots_init):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.setMinimumSize(0, 0)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding)

        self.descriptionLabel.setTextFormat(QtCore.Qt.RichText)
        self.descriptionLabel.setWordWrap(True)
        self.descriptionLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.descriptionLabel.setOpenExternalLinks(True)

        self.descriptionLabel.setText("""
            <div style="text-align:center; font-family:'Segoe UI', Arial;">
                <p style="font-size: 12pt; color:#444; margin:0 40px 10px 40px;">
                    Introduce the <b>experiment path</b> to begin analysis.
                </p>
                <p style="font-size: 11pt; color:#666; margin:0 40px;">
                    <b style="color:#ec407a;">Important:</b> The folder must contain a <b>settings.json</b> file.
                </p>
            </div>
        """)
