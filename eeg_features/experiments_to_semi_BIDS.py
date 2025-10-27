import re
import shutil
from pathlib import Path

def convert_to_semi_bids(input_path, output_path, anat):
    '''
    output_path/
    │
    ├── sub-01/
    │   └── ses-01/
    │       └── eeg/
    │           ├── sub-01_task-artifacts.rec.bson
    │           ├── sub-01_task-rest_run-01.rec.bson
    │           ├── sub-01_task-rest_run-02.rec.bson
    │           ├── sub-01_task-videogame_level-01.rec.bson
    │           ├── sub-01_task-videogame_level-02.rec.bson
    │           └── ...
    │
    ├── sub-02/
    │   └── ses-01/
    │       └── eeg/
    │           ├── sub-02_task-artifacts.rec.bson
    │           ├── sub-02_task-rest_run-01.rec.bson
    │           ├── sub-02_task-videogame_level-01.rec.bson
    │           └── ...
    │
    └── ...
        '''
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    subject_pattern = re.compile(r'(?:sujeto[_\s-]*|sub[_\s-]*|s)(\d+)', re.IGNORECASE)
    session_pattern = re.compile(r'(?:sesion[_\s-]*|session[_\s-]*|ses[_\s-]*)(\d+)', re.IGNORECASE)
    record_pattern = re.compile(r'R(\d+)', re.IGNORECASE)

    for subj_dir in input_path.iterdir():
        if not subj_dir.is_dir():
            continue

        subj_match = subject_pattern.search(subj_dir.name)
        if not subj_match:
            print(f"Ignoring folder not recognized as subject: {subj_dir.name}")
            continue

        subj_id = subj_match.group(1).zfill(2)
        subj_bids_path = output_path / f"sub-{subj_id}"
        subj_bids_path.mkdir(exist_ok=True)

        # Sessions
        sessions = [d for d in subj_dir.iterdir() if d.is_dir() and session_pattern.search(d.name)]

        if sessions:
            for ses_dir in sessions:
                ses_match = session_pattern.search(ses_dir.name)
                ses_id = ses_match.group(1).zfill(2)
                ses_bids_path = subj_bids_path / f"ses-{ses_id}"
                ses_bids_path.mkdir(exist_ok=True)
                process_recordings(ses_dir, ses_bids_path, anat)
        else:
            process_recordings(subj_dir, subj_bids_path, anat)

    print("✅ Conversion to format semi-BIDS completed.")


def process_recordings(source_dir, dest_root, anat):
    anat_dir = dest_root / str(anat)
    anat_dir.mkdir(parents=True, exist_ok=True)

    record_pattern = re.compile(r'R(\d+)', re.IGNORECASE)

    for file in source_dir.iterdir():
        if not file.is_file():
            continue

        suffixes = ''.join(file.suffixes).lower()
        if not suffixes.endswith(".rec.bson"): # valid files
            continue

        match = record_pattern.search(file.stem)
        if not match:
            continue

        r_number = int(match.group(1))
        task, level = determine_task_and_level(r_number)

        anat_dir.mkdir(parents=True, exist_ok=True)

        if task == "videogame":
            new_name = f"{dest_root.name}_task-{task}_level-{level:02d}"
        elif task == "rest":
            new_name = f"{dest_root.name}_task-{task}_run-{level:02d}"

        else:
            new_name = f"{dest_root.name}_task-{task}"

        dest_file = anat_dir / new_name
        shutil.copy2(file, str(dest_file) + '.rec.bson')
        print(f"Copying: {file.name} → {dest_file.relative_to(dest_root)}")


def determine_task_and_level(r_number):
    if r_number == 1:
        return "artifacts", None
    if r_number % 2 == 0:
        level = (r_number) // 2  # R3->1, R5->2, ..., R17->8
        return "rest", level
    else:
        level = (r_number - 1) // 2  # R3->1, R5->2, ..., R17->8
        return "videogame", level

input_path = r'D:\Proyectos\medusa-analyzer\BIE\raw'
output_path = r'D:\Proyectos\medusa-analyzer\BIE\BIDS'

convert_to_semi_bids(input_path, output_path, 'eeg')
