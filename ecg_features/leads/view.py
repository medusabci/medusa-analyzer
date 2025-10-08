from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import loadUiType
from PySide6.QtWidgets import QHBoxLayout, QCheckBox, QLabel, QComboBox, QWidget
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt


# Load UI class
ui_leads_widget = loadUiType("ecg_features/leads/view.ui")[0]

class LeadsWidget(QtWidgets.QWidget, ui_leads_widget):
    shown = QtCore.Signal()

    """
    Main widget element. Shows a list of channels and allows the user to select which ones to save and to which lead they correspond.
    """
    def __init__(self, main_window):
        super().__init__()
        self.setupUi(self)
        self.main_window = main_window


        ### LEADS HEADER ###
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.topContentWidget.setLayout(layout)
        self.label = QtWidgets.QLabel()
        self.label.setTextFormat(QtCore.Qt.RichText)
        self.label.setWordWrap(True)
        self.label.setText("""
            <div style="text-align:center; font-family:'Segoe UI', Arial;">
                <p style="font-size: 12pt; color:#444; margin:0 40px 10px 40px;">
                    Select the <b style="color:#007acc;">ECG channels</b> from your loaded signals 
                    and assign them to their corresponding <b style="color:#ec407a;">standard leads</b>.
                </p>

                <p style="font-size: 11pt; color:#666; margin:0 40px;">
                    This step ensures that each channel is correctly mapped before continuing with 
                    preprocessing and parameter extraction.
                </p>
            </div>
        """)
        # Remove background
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Base, palette.color(QtGui.QPalette.Window)) # For this element, Base color will be Window color
        self.topContentWidget.setPalette(palette)
        self.topContentWidget.setFrameShape(QtWidgets.QFrame.NoFrame)
        layout.addWidget(self.label)

        ### ELEMENT CONFIGURATION ###
        pixmap = QPixmap("media/ECG_Leads.png")
        scaled_pixmap = pixmap.scaled(
            int(pixmap.width() * 0.75),
            int(pixmap.height() * 0.75),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.imageLabel.setScaledContents(False)  # False to avoid distortion
        self.imageLabel.setPixmap(scaled_pixmap)
        self.imageLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Multiselection for conditions List
        self.conditionList.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        # Set explanatory text
        self.explanationLabel.setWordWrap(True)
        self.explanationLabel.setText("""
            <div style="text-align:left; font-family:'Segoe UI', Arial;">
                <p style="font-size: 11pt; color:#666">
                    Select the experimental conditions for ECG processing. Each selected condition will be analyzed 
                    separately. If no condition is selected, the entire recording will be processed without distinction
                    between conditions.
                </p>
            </div>
        """)

    def showEvent(self, event):
        super().showEvent(event)
        self.add_leads_rows()
        self.shown.emit()


    def add_leads_rows(self):
        """
        Function that adds a row with a checkbox, a label and a combobox for each lead in the biosignal info.
        """
        # Get the leads from the biosignal info
        files = self.main_window.stackedWidget.widget(1)
        leads = files.controller.biosignal_info['chan_name']

        # Clear existing layout if any
        self._clear_layout(self.LeadsSelection.layout())

        for i in range(len(leads)):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)  # Horizontal layout for each row

            # Checkbox
            checkbox = QCheckBox()
            checkbox.setObjectName(f"chan{i}CBox")
            checkbox.setText(f"Channel {leads[i]}")
            # checkbox.setChecked(True)

            # ComboBox
            combo = QComboBox()
            combo.setObjectName(f"chan{i}Combo")
            combo.addItems(["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"])

            # Create the layout, including the checkbox and the label
            row_layout.addWidget(checkbox)
            row_layout.addWidget(QLabel(f" - Lead: "))
            row_layout.addWidget(combo)
            row_layout.addStretch() # Horizontal spacer to push items to the left

            # Add the roe to the GroupBox layout
            self.LeadsSelection.layout().addWidget(row_widget)

    def _clear_layout(self, layout):
        """
        Recursively clear all widgets and sub-layouts inside a given layout.
        This is useful when you want to dynamically rebuild a layout without leftover widgets.
        """
        if layout is not None:
            # While there are items in the layout
            while layout.count():
                # Remove the first item from the layout
                item = layout.takeAt(0)
                # Check if the item is a widget
                widget = item.widget()
                if item.widget():
                    # Safely delete the widget (to avoid problems)
                    widget.deleteLater()
                # If the item is a sub-layout
                elif item.layout():
                    # Recursively clear the sub-layout
                    self._clear_layout(item.layout())
