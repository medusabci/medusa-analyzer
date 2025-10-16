from plots_stats.main_module.flow import on_next_click, on_back_click

class MainModuleWindowController:
    def __init__(self, ui):
        self.view = ui
        self.view.controller = self
        self.groups = {}

        # Buttons connectors
        self.view.nextButton.clicked.connect(lambda: on_next_click(self))
        self.view.backButton.clicked.connect(lambda: on_back_click(self))