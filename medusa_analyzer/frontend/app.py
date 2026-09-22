import sys
import logging
import os
from pathlib import Path

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PySide6.QtCore import Qt # Importar Qt para los modificadores de escalado

from medusa_analyzer.frontend.dashboard import DashboardPage, build_dashboard_catalog
from medusa_analyzer.frontend.experiments import create_experiment_page, discover_experiments
from medusa_analyzer.frontend.router import Router
from medusa_analyzer.frontend.splash import SplashScreen
try:
    import pyi_splash
except ImportError:
    pyi_splash = None

logger = logging.getLogger(__name__) # logger para que cuando haya un error sea vea de dónde viene

# Punto de entrada visual de tu aplicación: crea la ventana principal, carga los experimentos disponibles,
# monta el dashboard, registra rutas y arranca Qt. NOTA IMPORTANTE: el addWidget al stackWidget se hace dentro
# del router
def _log_file_path() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / "AppData" / "Local"
    return root / "MedusaAnalyzer" / "MedusaAnalyzer.log"


def _configure_logging() -> Path:
    log_path = _log_file_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )

    def _handle_exception(exc_type, exc_value, exc_traceback):
        logging.getLogger(__name__).exception(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = _handle_exception
    return log_path


def _configure_windows_app_id() -> None:
    if sys.platform != "win32":
        return

    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "MedusaBCI.MedusaAnalyzer"
        )
    except Exception:
        logger.debug("Could not set Windows application ID", exc_info=True)


def _application_icon() -> QIcon:
    return QIcon(str(_style_asset_path("medusa_task_icon.png")))


class MainWindow(QMainWindow):
    def __init__(self, splash: SplashScreen = None):
        super().__init__()
        self.setWindowTitle("Medusa Analyzer")
        self.setWindowIcon(_application_icon())
        self.resize(1200, 800)
        self.setMinimumSize(1020, 700)

        if splash is not None:
            splash.set_state(15, "Preparing interface...")

        stack = QStackedWidget() # Creamos el stackWidget, que es el contenedor principal de páginas
        self.setCentralWidget(stack)
        # Creamos un router y le pasamos el stack. El router usará ese stack para registrar páginas y cambiar entre ellas
        self.router = Router(stack)

        self.experiments = [] # aquí se guardan los experimentos que hay definidos
        self.pages = {} # diccionario para guardas las páginas de cada experimento
        experiment_definitions = discover_experiments()
        total_experiments = max(1, len(experiment_definitions))
        # Buscamos todos los experimentos disponibles y los recorremos uno a uno
        for index, definition in enumerate(experiment_definitions, start=1):
            if splash is not None:
                title = definition.info.get("title", definition.id.upper())
                progress = 20 + (50 * (index - 1) / total_experiments)
                splash.set_state(progress, f"Loading {title}...")
            logger.info("Loading experiment '%s' from %s", definition.id, definition.root)
            try:
                # Creamos el WorkflowShell con los widget del experimento
                page = create_experiment_page(definition)
            except Exception as exc:
                logger.exception("Skipping experiment '%s': %s", definition.id, exc)
                continue
            self.experiments.append(definition)
            self.pages[definition.route] = page # Guardamos todas las páginas de experimentos bajo la key de la ruta

        if splash is not None:
            splash.set_state(75, "Building dashboard...")

        categories, items = build_dashboard_catalog(self.experiments)
        # Creamos el dashboard con las categorías y los items detectados
        self.dashboard = DashboardPage(categories, items)
        # Conectamos una señal del dashboard con el router. Por ejemplo, cuando el dashboard emita
        # 'route_requested.emit("experiments/eeg")', se ejecutará 'self.router.navigate("experiments/eeg")'.
        # O sea, al hacer click en un experimento, navega a esa página.
        self.dashboard.route_requested.connect(self.router.navigate)

        # Registramos la página dashboard en el router con la ruta "dashboard". Después se podrá hacer
        #'self.router.navigate("dashboard")'
        self.router.register("dashboard", self.dashboard)

        if splash is not None:
            splash.set_state(85, "Registering routes...")

        for route, page in self.pages.items():
            self.router.register(route, page) # Registramos cada página del experimento en el router
            # Conectamos la señal de dashboard_dequested de cada página del workflow con volver al dashboard
            page.dashboard_requested.connect(lambda: self.router.navigate("dashboard"))
        logger.info("Registered routes: %s", sorted(self.router.routes))
        self.router.navigate("dashboard") # Navegamos al dashboard para empezar ahí
        if splash is not None:
            splash.set_state(100, "Ready")


def _load_stylesheet() -> str:
    path = Path(__file__).resolve().parent / "styles" / "main.qss"
    return path.read_text(encoding="utf-8").replace("${STYLE_DIR}", path.parent.as_posix())


def _style_asset_path(filename: str) -> Path:
    return Path(__file__).resolve().parent / "styles" / filename

def run() -> int:
    log_path = _configure_logging()
    logger.info("Starting Medusa Analyzer. frozen=%s executable=%s cwd=%s log=%s",
        bool(getattr(sys, "frozen", False)), sys.executable, Path.cwd(), log_path)
    _configure_windows_app_id()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Medusa Analyzer") # Ponemos el nombre de la aplicación
    app.setOrganizationName("Medusa BCI")
    # Icono de toda la aplicación
    icon = _application_icon()
    app.setWindowIcon(icon)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(_load_stylesheet()) # Carga el QSS y se lo aplicamos a toda la aplicación

    splash = SplashScreen()
    splash.splash_screen.setWindowIcon(icon)
    splash.set_state(5, "Starting MEDUSA Analyzer...")

    # # Ya puedes cerrar el splash de PyInstaller
    if pyi_splash is not None and pyi_splash.is_alive():
        splash.set_state(10, "Closing bootstrap splash...")
        pyi_splash.close()

    # Ejecutamos toodo el constructor de la MainWidow (crear el stack, router, descubrir experimentos, crear páginas,
    # registrar rutas y navegar al dashboard.
    window = MainWindow(splash=splash)
    window.show()

    # 4. Cerrar el splash screen transicionando a la ventana principal
    splash.hide(window)

    return app.exec()
