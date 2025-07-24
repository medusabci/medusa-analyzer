from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QMessageBox, QFrame
)


class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class QHLineStrong(QFrame):
    def __init__(self):
        super(QHLineStrong, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)

        # Make the line stronger
        self.setFixedHeight(4)
        self.setLineWidth(4)  # Visual border width


class ParameterWidget(QWidget):
    def __init__(self):
        super().__init__()

        # Box layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Labels
        header_label = QLabel("Select the parameters you want to compute")
        signal_label = QLabel("SIGNAL METRICS")
        signal_spc_label = QLabel("Spectral")
        signal_nln_label = QLabel("Non-linear")
        conn_label = QLabel("CONNECTIVITY METRICS")
        conn_amp_label = QLabel("Amplitude-based")
        conn_phs_label = QLabel("Phase-based")
        conn_spe_label = QLabel("Time-frequency-based")
        graph_label = QLabel("GRAPH METRICS")

        # Parameter button
        self.param_button = QPushButton("Next¡¿¡¡¡¿¿¿¿¿¿¿¡¡1!!!!!!!")
        self.param_button.setFixedHeight(40)
        self.param_button.clicked.connect(self.next_section)

        # LAYOUT CREATION

        # Title
        layout.addWidget(header_label)

        # Signal metrics
        layout.addWidget(QHLineStrong())
        layout.addWidget(signal_label)
        layout.addWidget(QHLine())
        layout.addWidget(signal_spc_label)
        layout.addSpacing(20)
        layout.addWidget(QHLine())
        layout.addWidget(signal_nln_label)
        layout.addSpacing(20)

        # Connectivity metrics
        layout.addWidget(QHLineStrong())
        layout.addWidget(conn_label)
        layout.addWidget(QHLine())
        layout.addWidget(conn_amp_label)
        layout.addSpacing(20)
        layout.addWidget(QHLine())
        layout.addWidget(conn_phs_label)
        layout.addSpacing(20)
        layout.addWidget(QHLine())
        layout.addWidget(conn_spe_label)
        layout.addSpacing(20)

        # Graph metrics
        layout.addWidget(QHLineStrong())
        layout.addWidget(graph_label)
        layout.addSpacing(20)

        # Final button
        layout.addWidget(self.param_button)

    def next_section(self):
        print('Holaaaaa :-)')

