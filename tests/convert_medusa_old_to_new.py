from medusa.core.legacy.recording import Recording as LegacyRecording
from medusa.core.legacy.convert import edubiomat_recording_to_v2
# from medusa.core import components
from pathlib import Path

files = list(Path(r"C:\Users\1993_\Desktop\OneDrive_1_21-9-2026\Claramente nervioso").rglob("*.bson"))

for idx,file in enumerate(files):
    print(files)
    mds_old = LegacyRecording.load(str(file))
    # subject = str(file.parent.name).split('-')[1]
    subject = str(idx)
    mds_new = edubiomat_recording_to_v2(mds_old)
    mds_new.bids.subject = subject
    mds_new.save(rf'C:\Users\1993_\Desktop\AAAAA\sub-{mds_new.bids.subject}_task-{mds_new.bids.task}.h5', data_format='h5')