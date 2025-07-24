import os
from os.path import basename, splitext
from copy import deepcopy
import medusa
from core.preprocessing import apply_preprocessing, band_segmentation
from core.segmentation import segment_by_condition, segment_by_event
from core.parameters import compute_parameters
from core.utils import save_outputs


def run_pipeline(settings_dic, selected_folder, checkboxes, progress_callback):
    selected_files = settings_dic['preprocessing'].get('selected_files', [])
    total_files = len(selected_files)

    band_seg = settings_dic['parameters'].get('band_segmentation', False)
    bands = settings_dic['parameters'].get('selected_bands', []) if band_seg else [
        {'name': 'broadband', 'min': settings_dic['parameters']['broadband_min'], 'max': settings_dic['parameters']['broadband_max']}
    ]

    total_steps = total_files * len(bands)

    for i, file in enumerate(selected_files):
        try:
            base_name = splitext(basename(file))[0]
            data = medusa.components.Recording.load(file)
            current_signal = data.eeg.signal
            fs = data.eeg.fs

            segmentation_type = settings_dic['segmentation']['segmentation_type']
            norm = settings_dic['segmentation']['norm'] or None

            for j, band in enumerate(bands):
                band_name = band.get('name', 'unknown')
                bp_min, bp_max = band.get('min'), band.get('max')

                if settings_dic['preprocessing'].get('apply_preprocessing'):
                    cfg = {**settings_dic['preprocessing']}
                    if band_seg:
                        cfg.update({'bp_min': bp_min, 'bp_max': bp_max, 'bp_order': 1000})
                        signal_to_process = current_signal.copy()
                    else:
                        signal_to_process = current_signal

                    processed_signal = apply_preprocessing(signal_to_process, fs, cfg)
                    data.eeg.signal = processed_signal
                    save_outputs(deepcopy(data), base_name, band_name, 'prep', selected_folder, checkboxes)
                else:
                    if band_seg:
                        processed_signal = band_segmentation(current_signal.copy(), bp_min, bp_max, fs)
                        data.eeg.signal = processed_signal
                    else:
                        processed_signal = current_signal

                if segmentation_type == 'condition':
                    segment_by_condition(
                        data, processed_signal, settings_dic, base_name, norm,
                        band=band_name if band_seg else None,
                        save_fn=lambda *args: save_outputs(*args, selected_folder, checkboxes),
                        compute_fn=compute_parameters
                    )
                elif segmentation_type == 'event':
                    segment_by_event(
                        data, processed_signal, settings_dic, base_name, norm, fs,
                        band=band_name if band_seg else None,
                        save_fn=lambda *args: save_outputs(*args, selected_folder, checkboxes),
                        compute_fn=compute_parameters
                    )

                global_progress = int(((i * len(bands) + j + 1) / total_steps) * 100)
                progress_callback(global_progress, f"Procesando: {basename(file)}")

        except Exception as e:
            print(f"Error al procesar {file}: {e}")
