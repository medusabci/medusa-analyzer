from PySide6 import QtWidgets, QtCore
from PySide6.QtUiTools import loadUiType

ui_plots_init = loadUiType('plots_stats/config/view.ui')[0]

class ConfigWidget(QtWidgets.QWidget, ui_plots_init):
    def __init__(self, main_module):
        super().__init__()
        self.setupUi(self)
        self.main_module = main_module

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

        # Generate the between and within descriptions
        self.betweenDescription.setText("""
            <div style="text-align:left; font-family:'Segoe UI', Arial;">
                <p style="font-size: 9pt; color:#666; margin:0 40px;">
                    A between-subjects analysis compares different groups of participants to examine the effect of an 
                    independent variable. Each participant is assigned to only one group, so measurements are 
                    independent across groups. Differences in outcomes reflect variations between these groups rather 
                    than within individuals. This design is useful when repeated measurements on the same participant 
                    are not feasible or may cause carryover effects.
                </p>
            </div>
        """)
        self.withinDescription.setText("""
            <div style="text-align:left; font-family:'Segoe UI', Arial;">
                <p style="font-size: 9pt; color:#666; margin:0 40px;">
                    A within-subjects analysis compares the same participants under multiple conditions or over time. 
                    Each participant serves as their own control, reducing variability due to individual differences. 
                    Differences in outcomes reflect changes within the same individuals across conditions. This design
                    increases statistical power but may require counterbalancing to avoid order effects.
                </p>
            </div>
        """)
        self.nocomparationDescription.setText("""
            <div style="text-align:left; font-family:'Segoe UI', Arial;">
                <p style="font-size: 9pt; color:#666; margin:0 40px;">
                    A no-comparison analysis focuses on the inspection of a single recording from one participant, without
                    comparing it to other subjects or conditions. The goal is descriptive or exploratory, allowing visualization
                    of signals, features, or metrics within an individual.
                </p>
            </div>
        """)
        self.betweenDescription.setWordWrap(True)
        self.withinDescription.setWordWrap(True)
        self.nocomparationDescription.setWordWrap(True)
        self.betweenDescription.mousePressEvent = lambda event: self.betweenRButton.setChecked(True)
        self.withinDescription.mousePressEvent = lambda event: self.withinRButton.setChecked(True)
        self.nocomparationDescription.mousePressEvent = lambda event: self.nocomparationRButton.setChecked(True)

        # Default to within-subjects
        self.withinRButton.setChecked(True)
