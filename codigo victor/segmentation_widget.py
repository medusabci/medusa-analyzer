from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QLabel, QPushButton, QAbstractItemView,
    QFileDialog, QRadioButton, QButtonGroup, QSpinBox,
    QAbstractSpinBox, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontMetrics
from collections import Counter
from Segmentation.utils import extract_condition_events


class SegmentationWidget(QWidget):
    def __init__(self):
        super().__init__()

        # Initialize varaibles
        self.conditions = []
        self.events = []

        # Box layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # File select button
        self.select_button = QPushButton("Select files...")
        self.select_button.clicked.connect(self.select_files)
        self.select_label = QLabel("Selected files: ")

        # Conditions
        self.condition_list = QListWidget()
        self.condition_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.condition_list.itemSelectionChanged.connect(self.update_labels)
        self.condition_label = QLabel("Selected conditions: ")

        # Events
        self.event_list = QListWidget()
        self.event_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.event_list.itemSelectionChanged.connect(self.update_labels)
        self.event_label = QLabel("Selected events: ")

        # Radio buttons
        self.rb1 = QRadioButton("Condition-wise")
        self.rb2 = QRadioButton("Event-wise")
        segmentation_buttons = QButtonGroup(self)
        segmentation_buttons.addButton(self.rb1)
        segmentation_buttons.addButton(self.rb2)
        self.segmentation_label = QLabel('Segmentation type: ')
        self.rb1.toggled.connect(lambda checked: self.rb_click(self.rb1, checked))
        self.rb2.toggled.connect(lambda checked: self.rb_click(self.rb2, checked))
        self.rb1.setDisabled(True)
        self.rb2.setDisabled(True)

        # Trial windows
        self.placeholder_label = QLabel("")
        self.placeholder_label.setFixedHeight(20)
        self.tr_label = QLabel("Trial length (ms): ")
        self.tr_box = QSpinBox()
        self.tr_box.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.tr_box.setRange(0, 99999)
        self.win_label1 = QLabel("Window interval (ms): ")
        self.win_label2 = QLabel("from")
        self.win_label3 = QLabel("to")
        self.win_box1 = QSpinBox()
        self.win_box2 = QSpinBox()
        self.win_box1.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.win_box1.setRange(-999999, 99999)
        self.win_box2.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.win_box2.setRange(0, 99999)
        self.tr_label.hide()
        self.tr_box.hide()
        self.win_label1.hide()
        self.win_label2.hide()
        self.win_label3.hide()
        self.win_box1.hide()
        self.win_box2.hide()

        # Segment button
        self.segment_button = QPushButton("Next¡¿¡¡¡¿¿¿¿¿¿¿¡¡1!!!!!!!")
        self.segment_button.setFixedHeight(40)
        self.segment_button.clicked.connect(self.next_section)
        self.segment_button.setDisabled(True)

        # LAYOUT CREATION

        # Row 1
        row1 = QHBoxLayout()
        row1.addWidget(self.select_button, 1)
        row1.addWidget(self.select_label, 6)
        layout.addLayout(row1)

        # Row 2
        row2 = QHBoxLayout()
        row2.addWidget(self.condition_list)
        row2.addWidget(self.event_list)
        layout.addLayout(row2)

        # Row 3
        layout.addWidget(self.condition_label)

        # Row 4
        layout.addWidget(self.event_label)

        # Row 5
        row5 = QHBoxLayout()
        row5.addWidget(self.segmentation_label, 1)
        row5.addWidget(self.rb1, 1)
        row5.addWidget(self.rb2, 1)
        row5.addStretch(7)
        layout.addLayout(row5)

        # Row 6
        row6 = QHBoxLayout()
        row6.addWidget(self.placeholder_label)
        row6.addWidget(self.tr_label, 1)
        row6.addWidget(self.tr_box, 2)
        row6.addWidget(self.win_label1, 1)
        row6.addWidget(self.win_label2, 1)
        row6.addWidget(self.win_box1, 2)
        row6.addWidget(self.win_label3, 1)
        row6.addWidget(self.win_box2, 2)
        row6.addStretch(7)
        layout.addLayout(row6)

        # Row 7
        layout.addWidget(self.segment_button)

    def select_files(self):
        self.event_list.clear()
        self.condition_list.clear()

        # Dialog box to select the files
        files, _ = QFileDialog.getOpenFileNames(self, "Select files", "", "MEDUSA files (*.bson)")
        self.files = files

        # If files selected, add them to the label
        if files:
            names = [a.split("/")[-1] for a in files]
            new_text = "Selected files:    " + ", ".join(names)
            fm = QFontMetrics(self.select_label.font())
            elided_text = fm.elidedText(new_text, Qt.ElideRight, self.select_label.width())
            self.select_label.setText(elided_text)
            self.select_label.setToolTip("<br>".join(names))
        else:
            self.select_label.setText("Selected files: ")

        # Extract events and conditions from the files, and add them to the list
        conditions, events, events_condition = extract_condition_events(files)
        self.condition_list.addItems(sorted(set(conditions)))
        self.event_list.addItems(sorted(set(events)))
        self.conditions = conditions
        self.events = events
        self.events_condition = events_condition

    def update_labels(self):
        # Enable buttons
        self.rb1.setDisabled(False)
        self.rb2.setDisabled(False)

        # Get the selected conditions
        conditions = [item.text() for item in self.condition_list.selectedItems()]
        counter_conditions = Counter(self.conditions)
        counter_conditions = [(cnd, counter_conditions[cnd]) for cnd in conditions]

        # Get the selected events (depending whether to filter or not by events)
        if not conditions:
            events = [item.text() for item in self.event_list.selectedItems()]
            counter_events = Counter(self.events)
            counter_events = [(evt, counter_events[evt]) for evt in events]
        else:
            events = [item.text() for item in self.event_list.selectedItems()]
            filtered_events = [self.events[n_evt] for n_evt, evt in enumerate(self.events_condition) if evt in conditions]
            counter_events = Counter(filtered_events)
            counter_events = [(evt, counter_events[evt]) for evt in events]

        # Display in the labels
        self.condition_label.setText("Selected conditions: " + ", ".join(f"{cnd} ({count})" for cnd, count in counter_conditions))
        self.event_label.setText("Selected events: " + ", ".join(f"{evt} ({count})" for evt, count in counter_events))

        return counter_conditions, counter_events

    def rb_click(self, button, _):
        self.segment_button.setDisabled(False)

        # Activate (or deactivate) the list and change segmentation boxes layout
        if button == self.rb1:
            self.event_list.clearSelection()
            self.update_labels()
            self.event_list.setDisabled(True)
            self.tr_label.show()
            self.tr_box.show()
            self.win_label1.hide()
            self.win_label2.hide()
            self.win_label3.hide()
            self.win_box1.hide()
            self.win_box2.hide()
            self.placeholder_label.hide()
        else:
            self.event_list.setDisabled(False)
            self.tr_label.hide()
            self.tr_box.hide()
            self.win_label1.show()
            self.win_label2.show()
            self.win_label3.show()
            self.win_box1.show()
            self.win_box2.show()
            self.placeholder_label.hide()

    def next_section(self):
        # Error check
        if not self.rb1.isChecked() and not self.rb2.isChecked():
            return

        # Get the selected events and conditions
        conditions = [item.text() for item in self.condition_list.selectedItems()]
        events = [item.text() for item in self.event_list.selectedItems()]
        # To avoid start segmentation if zero trials are avaiable
        counter_conditions, counter_events = self.update_labels()

        # Error check and store the segmentation window values
        if self.rb2.isChecked():
            win = [self.win_box1.value(), self.win_box2.value()]
            if win == [0, 0]:
                QMessageBox.information(None, "Error", "Both segmentation values cannot be 0")
                return
            trial_sum = sum(value for _, value in counter_events)
        else:
            win = self.tr_box.value()
            if win == 0:
                QMessageBox.information(None, "Error", "Trial size cannot be 0")
                return
            trial_sum = sum(value for _, value in counter_conditions)

        # if no events, throw an error
        if trial_sum == 0:
            QMessageBox.information(None, "Error", "There are no trials to segment")
            return

        # Ask whether to save the segmented files
        save_confirmation = QMessageBox.question(None, "Save?", "Do you want to save the segmented files?", QMessageBox.Yes | QMessageBox.No)
        save_confirmation = save_confirmation == QMessageBox.Yes
        if save_confirmation:
            save_folder = QFileDialog.getExistingDirectory(None, "Select saving folder")
        else:
            save_folder = None

        # segmented_signal, segmented_signal_lbl = do_segmentation.do_segementation(self.files, conditions, events, win, save_folder)

        self.segmentation_info ={
            "files": self.files,
            "conditions": conditions,
            "events": events,
            "win": win,
            "save_folder": save_folder
        }

        self.window().param_view()

        print("Segmented signals available")
