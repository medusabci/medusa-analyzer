from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Callable

"""Script que valida una carpeta con tructura BIDS"""

# Extensiones consideradas como archivos de datos raw
# TODO: depende del experimento. esto es lo de eeg. Quitar de aqui.
RAW_EXTENSIONS = {".edf", ".vhdr", ".vmrk", ".eeg", ".set", ".fdt", ".bdf", ".mpl"}
# Sufijos de tablas auxiliares BIDS que el código va a buscar
# TODO: al igual que lo anterior, estos campos no son generales de bids, dependen del tipo
#  de señal entonces dependen del experimento. Hay que quitarlo de aqui. Si eso podemos
#  dejar esta clase general para que permita meter validaciones especçificas desde el
#  experimento, que es donde meteríamos estas cosas.
SIDE_TABLE_SUFFIXES = ("channels", "events", "electrodes", "optodes")


def parse_bids_name(path: Path) -> dict[str, Any]:
    """Función que devuelve un diccionario con la información extraída del nombre del archivo."""
    # TODO: hay parcheo con lo del .tsv que hay que quitar
    # Quitamos la extensión del path proporcionado, que es el nombre del archivo
    stem = path.name[:-7] if path.name.lower().endswith(".tsv.gz") else path.stem
    # Dividimos el nombre por los guiones bajos para separar las entidades
    parts = stem.split("_")
    entities: dict[str, str] = {} # dic para guardar las entidades
    for part in parts[:-1]: # recorremos todas las entidades menos la última (la última es la señal)
        if "-" in part: # las entidades tienen forma clave-valor
            key, value = part.split("-", 1)
            entities[key] = value
    return {"suffix": parts[-1].lower() if parts else "", "entities": entities}


def validate_bids_dataset(root: str | Path, allowed_datatypes: list[str] | None = None,
    raw_extensions: list[str] | None = None, progress_callback: Callable[[int], None] | None = None,
    log_callback: Callable[[str, str], None] | None = None) -> dict[str, Any]:
    """
    :param root: carpeta ráiz del dataset BIDS
    :param allowed_datatypes: lista opcional de datatypes permitidos, por ejemplo ["eeg", "meg"]
    :param raw_extensions: lista opcional de extensiones raw permitidas
    :param progress_callback: función opcional para informar progreso
    :param log_callback: función opcional para registrar mensaje
    :return:
    TODO: no veo la diferencia entre allowed_datatyoes y raw extensions
    """

    root = Path(root)
    if not root.is_dir(): # Si no existe la carpera lanza un error
        raise ValueError(f"BIDS folder does not exist: {root}")

    allowed = {datatype.lower() for datatype in (allowed_datatypes or [])}
    extensions = {ext.lower() if str(ext).startswith(".") else f".{str(ext).lower()}"
        for ext in (raw_extensions or RAW_EXTENSIONS)}
    errors: list[str] = []
    warnings: list[str] = []

    if log_callback:
        log_callback(f"Validating BIDS dataset: {root}", "info")
    if progress_callback:
        progress_callback(5)
    if root.name.startswith(("sub-", "ses-")):
        errors.append("Select the BIDS dataset root, not a subject or session folder.")
    if not (root / "dataset_description.json").is_file():
        errors.append("Missing dataset_description.json at BIDS root.")
    if not any(path.is_dir() and path.name.startswith("sub-") for path in root.iterdir()):
        errors.append("No sub-* folders found at BIDS root.")

    # Recolección de archivos
    # Buscamos recursivamente todos los archivos dentro de root y filtramos los json y los tsv. Vamos a descartar los
    # ficheros que no estén en el root o en carpeta que empiecen por sub
    all_paths = list(root.rglob("*"))
    files = []

    for index, path in enumerate(all_paths):
        if path.is_file() and (
                path.parent == root or
                path.relative_to(root).parts[0].startswith("sub")
        ):
            files.append(path)

        if progress_callback:
            progress_callback(
                5 + int((index + 1) / max(len(all_paths), 1) * 10)
            )

    json_files = [path for path in files if path.suffix.lower() == ".json"]
    tsv_files = [path for path in files if path.suffix.lower() == ".tsv"]

    # Creamos una lista para guardar los registros raw encontrados
    recordings: list[dict[str, Any]] = []
    if log_callback:
        log_callback(f"Found {len(files)} file(s): {len(json_files)} JSON sidecar(s), {len(tsv_files)} TSV sidecar(s).",
            "info")
        if allowed:
            log_callback(f"Allowed datatype(s): {', '.join(sorted(allowed))}.", "info")
        log_callback(f"Allowed raw extension(s): {', '.join(sorted(extensions))}.", "info")

    # Recorremos todos los archivos encontrados
    for index, path in enumerate(files, start=1):
        ext = path.suffix.lower() # extensión del archivo
        if ext not in extensions or ext in {".json", ".tsv"}:
            continue
        # TODO: esto que viene ahora es parcheo, no es nada general. Además depende de que sea
        #  de un experimento con señales de EEG, NO ES GENERAL
        if ext == ".vmrk" or (ext == ".eeg" and path.with_suffix(".vhdr").is_file()):
            continue
        if ext == ".fdt" and path.with_suffix(".set").is_file():
            continue

        # Tomamos como datatype el nombre de la capeta padre
        datatype = path.parent.name.lower()
        # Si se especificaron datatypes permitidos y este archivo no pertenece a uno de ellos, continuamos
        if allowed and datatype not in allowed:
            continue

        # Calculamos el dic de key-value de todas las entidades del nombre del archivo
        parsed = parse_bids_name(path)
        entities = parsed["entities"]
        if not entities.get("sub"): # Comprobamos que haya sujeto
            warnings.append(f"Raw file without sub- entity: {path.relative_to(root)}")
            # TODO: no debería ser ya error??? Y lo siguiente también??
        if parsed["suffix"] != datatype: # Compramos que el sufijo del archivo coincida con el datatype
            warnings.append(f"Raw suffix '{parsed['suffix']}' does not match datatype '{datatype}': {path.relative_to(root)}")

        metadata, json_sidecars = {}, []

        # Buscamos JSON aplicables a este archivo raw y los ordena. Llama a _applicable_sidecars()
        # para encontrar JSON compatibles con el archivo actual. Luego los ordena usando _sidecar_score().
        # La idea es aplicar primero los más generales y después los más específicos.
        for sidecar, _ in sorted(_applicable_sidecars(root, path.parent, entities, parsed["suffix"], json_files),
            key=lambda item: _sidecar_score(root, item[0], item[1])):
            try:
                data = _read_json(sidecar) # lee JSON y devuelve un dic
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"Could not read JSON sidecar {sidecar.relative_to(root)}: {exc}")
                continue
            metadata.update(data) # Combinamos los metadatos leídos con los anteriores
            json_sidecars.append(str(sidecar)) # Guarda la ruta del sidecar JSON aplicado

        sidecars: dict[str, str] = {} # guardar rutas de sidecars TSV encontrados
        tables: dict[str, list[dict[str, str]]] = {} # guardar contenido de tablas TSV leídas
        for suffix in SIDE_TABLE_SUFFIXES: # TODO: está parcheado
            # Buscamos archivos compatibles con el sufijo actual. Por ejemplo, si suffix = "channels"
            # buscará archivos tipo "sub-01_task-rest_channels.tsv
            matches = _applicable_sidecars(root, path.parent, entities, suffix, tsv_files)
            if not matches:
                continue
            # Elegimos el sidecar TSV más específico. A diferencia del JSON, aquí solo se queda con uno.
            # TODO: cambiar nombre de función _sidecar_score() a algo que refleje el principio de herencia
            sidecar, _ = max(matches, key=lambda item: _sidecar_score(root, item[0], item[1]))
            sidecars[f"{suffix}_tsv"] = str(sidecar) # guardamos la ruta del TSV
            # TODO: como se gestionan sujetos con TSV diferentes???
            try:
                tables[suffix] = _read_tsv(sidecar) # lee y guarda el contenido
            except OSError as exc:
                errors.append(f"Could not read TSV sidecar {sidecar.relative_to(root)}: {exc}")

        # Añadimos un nuevo diccionario a la lista de registros
        recordings.append({
            "path": str(path),
            "relative_path": str(path.relative_to(root)),
            "datatype": datatype,
            "suffix": parsed["suffix"], # sufijo del nombre BIDS
            "extension": ext, # extensión del archivo
            "entities": entities, # entidades BIDS extraídas
            "metadata": metadata, # metadatos combinados desde JSON sidecars
            "json_sidecars": json_sidecars, # lista de JSON sidecars usados
            "sidecars": sidecars, # TSV sidecars encontrados
            "tables": tables, # tablas TSV leídas
        })

        # Si existe callback de progreso, actualiza el progreso
        if progress_callback:
            progress_callback(min(95, 15 + int(index / max(len(files), 1) * 80)))

    # Comprueba si no se encontró ningún registro raw compatible
    if not recordings:
        suffix = f" for datatypes {sorted(allowed)}" if allowed else ""
        errors.append(f"No compatible raw recordings found{suffix}.")

    if progress_callback:
        progress_callback(100)
    if log_callback:
        log_callback(f"Found {len(recordings)} raw recording(s).", "info")
        for error in errors:
            log_callback(error, "error")
        for warning in warnings:
            log_callback(warning, "warning")

    return {"root": str(root), "is_valid": not errors, "errors": errors, "warnings": warnings,
        "recordings": recordings}


def _applicable_sidecars(root: Path, recording_dir: Path, entities: dict[str, str], suffix: str,
    candidates: list[Path]) -> list[tuple[Path, dict[str, str]]]:
    """Busca sidecars que puedan aplicarse a un registro concreto."""
    matches = []
    for path in candidates: # Recorremos todos los archivos candidatos
        parsed = parse_bids_name(path) # Analiza el nombre BIDS del candidato
        # Comprobamos que el sufijo coincida, y que el sidecar esté en una carpeta padre o igual a
        # a la carpeta del regsitro
        if parsed["suffix"] != suffix or not _is_parent(path.parent, recording_dir):
            continue
        side_entities = parsed["entities"] # extraemos las entidades del sidecar
        # Comprobamos que todas las entidades del sidecar coincidan con las del archivo raw
        if all(entities.get(key) == value for key, value in side_entities.items()):
            matches.append((path, side_entities)) # añadimos sidecar como coincidencia
    # Devuelve todos los sidecars aplicables
    return matches


def _sidecar_score(root: Path, path: Path, entities: dict[str, str]) -> tuple[int, int]:
    """Calcula una puntuación para decidir qué sidecar es más específico. Principio de herencia."""
    try:
        # Calculamos cuántos niveles por debajo de la ráiz está el sidecar
        depth = len(path.parent.relative_to(root).parts)
    except ValueError:
        depth = 0
    return depth, len(entities)


def _is_parent(parent: Path, child: Path) -> bool:
    """Comprueba si parent es carpeta padre de child, o si son la misma ruta."""
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def _read_json(path: Path) -> dict[str, Any]:
    """Función para leer un JSON"""
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def _read_tsv(path: Path) -> list[dict[str, str]]:
    """Función para leer un TSV"""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


__all__ = ["parse_bids_name", "validate_bids_dataset"]
