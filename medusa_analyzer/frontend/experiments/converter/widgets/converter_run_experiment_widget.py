from medusa_analyzer.frontend.widgets.run_experiment import RunExperimentWidget
from medusa_analyzer.frontend.worker import Worker
from medusa_analyzer.backend.converter.run_conversion import run_conversion
from medusa_analyzer.backend.converter.other_database import build_other_database_bids

class ConverterRunExperimentWidget(RunExperimentWidget):
    """Run step específico para el experimento de conversión."""

    def __init__(self, experiment_info: dict, defaults: dict, state: dict):
        # Inicializa la clase padre genérica con los parámetros necesarios
        super().__init__(experiment_info, defaults, state)
        self.status_label.setText("Ready to run conversion.")

    def run_pipeline(self):
        """Start the converter pipeline in a background worker."""
        if self.pipeline_running:
            return

        self.pipeline_running = True
        self.state["completion_status"] = "incompleted"
        self.changed.emit()

        self.status_label.setText(f"Running {self.experiment_info['title']}...")
        self.clear_logs()
        self.log_callback(f"Starting {self.experiment_info['title']}...")
        self.set_progress(0)

        if self.state.get("source_type") == "other_database":
            context = self.state.get("other_db_conversion")
            if context is None:
                self._mark_pipeline_failed("Other DB conversion context is missing. Load the database again.")
                self.pipeline_running = False
                self.changed.emit()
                return
            context.output_root = self.state["output_path"]
            kwargs = {
                "context": context,
                "output_path": self.state["output_path"],
                "dataset_name": self.state.get("dataset_name"),
                "progress_callback": self.set_progress,
                "log_callback": self.log_callback
            }
            worker = Worker(build_other_database_bids, **kwargs)
        else:
            kwargs = {
                "input_data": self.state['input_data'],
                "output_path": self.state['output_path'],
                "extensions": self.defaults.get("load_data", {}).get("allowed_extensions", {}),
                "progress_callback": self.set_progress,
                "log_callback": self.log_callback
            }
            worker = Worker(run_conversion, **kwargs)

        worker.signals.progress.connect(self.set_progress)
        worker.signals.logging.connect(self.log_callback)
        worker.signals.result.connect(self._pipeline_completed)
        worker.signals.error.connect(self._pipeline_failed)
        worker.signals.finished.connect(self._pipeline_finished)
        self.runner.start(worker)
