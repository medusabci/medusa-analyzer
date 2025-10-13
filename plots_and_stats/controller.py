
from plots_and_stats.flow import on_next_click, on_back_click
from plots_and_stats.initial_configuration.controller import PlotStatsInitController
from plots_and_stats.initial_configuration.controller import PlotStatsInitController
from plots_and_stats.initial_configuration.view import PlotStatsInitView

class MainModuleWindowController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self
        self.total_steps = 0

        self.init_view = PlotStatsInitView()
        self.init_controller = PlotStatsInitController(self.init_view)
        self.init_controller.main_window_controller = self  # 👈 Aquí conectamos con el main window

        # Buttons connections
        self.view.nextButton.clicked.connect(lambda: on_next_click(self))
        self.view.backButton.clicked.connect(lambda: on_back_click(self))


