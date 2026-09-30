import json
from pathlib import Path
from collections import Counter


def _get_core_name(filename: str) -> str:
    """Extrae el nombre base del archivo omitiendo entidades dependientes (sub, ses, run)."""
    parts = filename.replace('.json', '').split('_')
    core_parts = [
        p for p in parts
        if not p.startswith('sub-')
        and not p.startswith('ses-')
        and not p.startswith('run-')
        and not p.startswith('acq-')
    ]
    return '_'.join(core_parts) + '.json'

def _read_json_as_str(path: Path) -> str:
    data = _load_json(path)
    return json.dumps(data, sort_keys=True)


def _load_json(path: Path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON file during inheritance pruning: {path}: {exc}") from exc


def _write_str_to_json(json_str: str, path: Path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(json.loads(json_str), f, indent=4)

def split_json(filepath: Path):
    """Divide el JSON aislando exclusivamente el bloque 'TaskInformation'."""
    data = _load_json(filepath)

    # Extraer el bloque completo de la tarea. Si no existe, devuelve None.
    task_info = data.pop('TaskInformation', None)

    # Eliminar el archivo original
    filepath.unlink()

    base_name = filepath.name.replace('.json', '')

    # Guardar temporal de Tarea (se mantiene la clave raíz para la correcta fusión posterior)
    if task_info is not None:
        with open(filepath.with_name(f"{base_name}_tempTask.json"), 'w', encoding='utf-8') as f:
            json.dump({"TaskInformation": task_info}, f, indent=4)

    # Guardar temporal de Hardware (el diccionario data ya no contiene 'TaskInformation')
    if data:
        with open(filepath.with_name(f"{base_name}_tempHw.json"), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)


def run_promotion(bids_root: Path, suffix: str):
    """Ejecuta el algoritmo de ascenso jerárquico para un sufijo temporal específico."""

    def _evaluate_and_promote(files_to_check, target_dir, prefix=""):
        """Agrupa, cuenta y promociona archivos si superan el umbral del 50%."""
        groups = {}
        for json_file in files_to_check:
            core = _get_core_name(json_file.name)
            groups.setdefault(core, []).append(json_file)

        for core_name, files in groups.items():
            total = len(files)
            if total <= 1:
                continue

            counts = Counter(_read_json_as_str(p) for p in files)
            most_common_str, most_common_count = counts.most_common(1)[0]

            if (most_common_count / total) > 0.5:
                promoted_path = target_dir / f"{prefix}{core_name}"
                _write_str_to_json(most_common_str, promoted_path)

                for file in files:
                    if _read_json_as_str(file) == most_common_str:
                        file.unlink()

    # 1. De Nivel Sesión a Nivel Sujeto
    for subject_dir in bids_root.glob("sub-*"):
        if not subject_dir.is_dir():
            continue

        subject_id = subject_dir.name
        session_jsons = [p for p in subject_dir.rglob(f"*{suffix}") if p.parent != subject_dir]

        # Ejecuta la promoción asignando el directorio del sujeto y su prefijo
        _evaluate_and_promote(session_jsons, target_dir=subject_dir, prefix=f"{subject_id}_")

    # 2. De Nivel Sujeto/Sesión a Raíz del Dataset
    all_jsons = []
    for subject_dir in bids_root.glob("sub-*"):
        if subject_dir.is_dir():
            all_jsons.extend(subject_dir.rglob(f"*{suffix}"))

    # Ejecuta la promoción a nivel raíz (sin prefijo)
    _evaluate_and_promote(all_jsons, target_dir=bids_root)


def merge_and_clean(directory: Path) -> None:
    """Busca archivos temporales en el directorio, los fusiona si coinciden y restaura el formato BIDS."""
    files = list(directory.glob("*_tempTask.json")) + list(directory.glob("*_tempHw.json"))
    base_groups = {}

    for f in files:
        base = f.name.replace('_tempTask.json', '.json').replace('_tempHw.json', '.json')
        base_groups.setdefault(base, []).append(f)

    for base_name, files in base_groups.items():
        merged_data = {}
        for file in files:
            merged_data.update(_load_json(file))
            file.unlink()

        final_path = directory / base_name
        with open(final_path, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, indent=4)


def prune_output(bids_root: Path):
    """Función principal orquestadora."""

    # Fase 0: División de archivos JSON
    for json_file in bids_root.rglob("*.json"):

        # Do not process dataset_description.json, participants.json, or temp.json files
        if json_file.name in ["dataset_description.json", "participants.json"]:
            continue
        if "_temp" in json_file.name:
            continue
        split_json(json_file)

    # Fase 1 y 2: Promoción jerárquica independiente
    run_promotion(bids_root, "_tempTask.json")
    run_promotion(bids_root, "_tempHw.json")

    # Fase 3: Fusión y limpieza
    for dir_path in [bids_root] + list(bids_root.rglob("*")):
        if dir_path.is_dir():
            merge_and_clean(dir_path)

    return None

# --- Ejemplo de Uso ---
if __name__ == "__main__":
    prune_output(r"D:\MEDUSA\medusa-analyzer-KEOPS\sample_data\bids_dataset")
