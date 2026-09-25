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

logger = logging.getLogger(__name__) # logger para que cuando haya un error sea vea de dónde viene

# Punto de entrada visual de tu aplicación: crea la ventana principal, carga los experimentos disponibles,
# monta el dashboard, registra rutas y arranca Qt. NOTA IMPORTANTE: el addWidget al stackWidget se hace dentro
# del router
TITLE_BAR_COLOR = "#181215"
TITLE_BAR_TEXT_COLOR = "#F7F1F3"
TITLE_BAR_BORDER_COLOR = "#3A2931"


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


def _colorref(hex_color: str) -> int:
    color = hex_color.strip().lstrip("#")
    if len(color) != 6:
        raise ValueError(f"Invalid color: {hex_color}")
    red = int(color[0:2], 16)
    green = int(color[2:4], 16)
    blue = int(color[4:6], 16)
    return red | (green << 8) | (blue << 16)


def _apply_windows_title_bar_theme(window: QMainWindow) -> None:
    if sys.platform != "win32":
        return

    try:
        import ctypes

        hwnd = ctypes.c_void_p(int(window.winId()))
        dark_mode = ctypes.c_int(1)
        caption_color = ctypes.c_int(_colorref(TITLE_BAR_COLOR))
        text_color = ctypes.c_int(_colorref(TITLE_BAR_TEXT_COLOR))
        border_color = ctypes.c_int(_colorref(TITLE_BAR_BORDER_COLOR))

        dwm = ctypes.windll.dwmapi
        for attribute in (20, 19):
            result = dwm.DwmSetWindowAttribute(
                hwnd,
                attribute,
                ctypes.byref(dark_mode),
                ctypes.sizeof(dark_mode),
            )
            if result == 0:
                break

        for attribute, value in (
            (35, caption_color),
            (36, text_color),
            (34, border_color),
        ):
            dwm.DwmSetWindowAttribute(
                hwnd,
                attribute,
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
    except Exception:
        logger.debug("Could not apply Windows title bar theme", exc_info=True)


def _application_icon() -> QIcon:
    return QIcon(str(_style_asset_path("medusa_task_icon.png")))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Medusa Analyzer")
        self.setWindowIcon(_application_icon())
        self.resize(1200, 800)
        self.setMinimumSize(1020, 700)

        stack = QStackedWidget() # Creamos el stackWidget, que es el contenedor principal de páginas
        self.setCentralWidget(stack)
        # Creamos un router y le pasamos el stack. El router usará ese stack para registrar páginas y cambiar entre ellas
        self.router = Router(stack)

        self.experiments = [] # aquí se guardan los experimentos que hay definidos
        self.pages = {} # diccionario para guardas las páginas de cada experimento
        experiment_definitions = discover_experiments()
        # Buscamos todos los experimentos disponibles y los recorremos uno a uno
        for definition in experiment_definitions:
            logger.info("Loading experiment '%s' from %s", definition.id, definition.root)
            try:
                # Creamos el WorkflowShell con los widget del experimento
                page = create_experiment_page(definition)
            except Exception as exc:
                logger.exception("Skipping experiment '%s': %s", definition.id, exc)
                continue
            self.experiments.append(definition)
            self.pages[definition.route] = page # Guardamos todas las páginas de experimentos bajo la key de la ruta

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

        for route, page in self.pages.items():
            self.router.register(route, page) # Registramos cada página del experimento en el router
            # Conectamos la señal de dashboard_dequested de cada página del workflow con volver al dashboard
            page.dashboard_requested.connect(lambda: self.router.navigate("dashboard"))
        logger.info("Registered routes: %s", sorted(self.router.routes))
        self.router.navigate("dashboard") # Navegamos al dashboard para empezar ahí
    def showEvent(self, event):
        super().showEvent(event)
        _apply_windows_title_bar_theme(self)


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

    # Ejecutamos toodo el constructor de la MainWidow (crear el stack, router, descubrir experimentos, crear páginas,
    # registrar rutas y navegar al dashboard.
    window = MainWindow()
    window.show()

    return app.exec()
