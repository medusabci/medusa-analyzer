from multiprocessing import freeze_support

from medusa_analyzer.main import main


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())

### python -m PyInstaller --clean --noconfirm main.spec
