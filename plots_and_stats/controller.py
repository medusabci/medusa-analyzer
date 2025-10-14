from plots_and_stats.initial_configuration.controller import PlotStatsInitController
from plots_and_stats.initial_configuration.view import PlotStatsInitView
from plots_and_stats.flow import on_next_click, on_back_click

class MainModuleWindowController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self

        # Crear la vista y el controlador de configuración inicial
        self.init_view = PlotStatsInitView(self.view)
        self.init_controller = PlotStatsInitController(self.init_view)

        # 👇 Esta línea es clave: aquí conectas el main window con el controlador
        self.init_controller.main_window_controller = self

        # Conexiones de botones
        self.view.nextButton.clicked.connect(lambda: on_next_click(self))
        self.view.backButton.clicked.connect(lambda: on_back_click(self))

        # Si necesitas mas ayuda, me dices, estaré aqui para tí. Un saludo ChatrGPT
