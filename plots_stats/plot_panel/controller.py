from PySide6 import QtWidgets, QtCore
from PySide6.QtUiTools import loadUiType
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class TabbedPlotWidgetController(QtCore.QObject):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.template_ui_path = 'plots_stats/plot_panel/tab_template.ui'

        self._tabs_created = False

        print("DEBUG Controller creado para view:", id(self.view))
        self.view.shown.connect(self.create_tabs)
        print("DEBUG Conectado signal shown a create_tabs del controller:", id(self))
        print(f"DEBUG Controller instanciado correctamente, view={id(self.view)} controller={id(self)}")
    def create_tabs(self):

        if self._tabs_created:
            print("DEBUG Tabs ya creados, ignorando.")
            return

        selected_parameters = getattr(self.view.main_module.controller, "params", None)
        if selected_parameters is None:
            return

        try:
            param_iter = list(selected_parameters)
        except Exception:
            param_iter = [str(selected_parameters)]

        tab_widget = self.view.tab_widget
        # Limpiar tabs previos
        while tab_widget.count() > 0:
            tab_widget.removeTab(0)

        for param in param_iter:
            tab = self.load_ui(self.template_ui_path, parent=tab_widget)

            # Cambiar título
            title_label = tab.findChild(QtWidgets.QLabel, "titleLabel")
            if title_label:
                title_label.setText(param)

            # Crear plot
            placeholder = tab.findChild(QtWidgets.QWidget, "plotPlaceholder")
            if placeholder is None:
                # si no hay placeholder, ignorar la creación del plot
                layout = None
            else:
                if placeholder.layout() is None:
                    layout = QtWidgets.QVBoxLayout(placeholder)
                    layout.setContentsMargins(0, 0, 0, 0)
                else:
                    layout = placeholder.layout()

            if layout is not None:
                fig = Figure(figsize=(5, 4))
                canvas = FigureCanvas(fig)
                ax = fig.add_subplot(111)

                # Aquí puedes dibujar datos reales más adelante; de momento draw vacío
                fig.tight_layout()
                layout.addWidget(canvas)
                canvas.draw()

            # fig = Figure(figsize=(5, 4))
            # canvas = FigureCanvas(fig)
            # ax = fig.add_subplot(111)
            # layout.addWidget(canvas)

            # Dibujar datos
            # values = self.param_data[param]
            # ax.bar(self.channels, values)
            # ax.set_title(param)
            # ax.tick_params(axis='x', rotation=90)
            # fig.tight_layout()
            # canvas.draw()

            # Conectar botones
            prev_btn = tab.findChild(QtWidgets.QPushButton, "prevButton")
            next_btn = tab.findChild(QtWidgets.QPushButton, "nextButton")
            export_btn = tab.findChild(QtWidgets.QPushButton, "exportButton")

            if prev_btn:
                prev_btn.clicked.connect(self.prev_tab)
            if next_btn:
                next_btn.clicked.connect(self.next_tab)
            if export_btn:
                export_btn.clicked.connect(lambda checked, t=tab: self.export_figure(t))

            # Agregar al QTabWidget principal
            self.view.add_tab(tab, str(param))

            self._tabs_created = True

    def load_ui(self, path, parent=None):
        """Carga un .ui y devuelve el widget resultante."""
        form_class, base_class = loadUiType(path)
        widget = base_class(parent) if parent is not None else base_class()
        ui = form_class()
        ui.setupUi(widget)
        return widget


    def prev_tab(self):
        current = self.view.tab_widget.currentIndex()
        if current > 0:
            self.view.tab_widget.setCurrentIndex(current - 1)

    def next_tab(self):
        current = self.view.tab_widget.currentIndex()
        if current < self.view.tab_widget.count() - 1:
            self.view.tab_widget.setCurrentIndex(current + 1)

    def export_figure(self, tab):
        print("Exportar figura del tab:", tab)
