from pathlib import Path

from tcia_utils import nbia

import pydicom
import os

class LidcIdriDownloader:
    patient_ids : list[str] = []
    patients_files_info : dict = {}
    dir_path : Path = ""


    def __init__(self, dir_path : Path | str):
        if isinstance(dir_path, str):
            dir_path = Path(dir_path)

        self.dir_path = dir_path

    def get_patient_path(self, pid) -> str :
        return str(self.dir_path / str(pid))

    def download(self, patient_ids : list[str]) -> None:
        """
        Retrieve DICOM from patient ids.
        :param patient_ids:
        :return:
        """
        self.patient_ids = patient_ids

        # Download
        for pid in self.patient_ids:
            series = nbia.getSeries(collection="LIDC-IDRI", patientId=pid)

            # Keep only CT and SEG
            ct_series = [s for s in series if s['Modality'] in ('CT', 'SEG')]

            print(f"\n{pid} - séries CT :")
            for s in ct_series:
                print(f"  UID: {s['SeriesInstanceUID']}")
                print(f"  Slices: {s['ImageCount']}")

            ct_uids = [s['SeriesInstanceUID'] for s in ct_series]
            nbia.downloadSeries(ct_uids, input_type="list", path=self.get_patient_path(pid))

            # get files info
            patient_path = self.get_patient_path(pid)
            subdirs = {d: len(os.listdir(os.path.join(patient_path, d)))
                       for d in os.listdir(patient_path)
                       if os.path.isdir(os.path.join(patient_path, d))}

            self.patients_files_info[pid] = subdirs

    def get_patient_files_info(self, pid):
        patient_path = self.get_patient_path(pid)
        for d, count in self.patients_files_info[pid].items():
            dcm_files = [f for f in os.listdir(os.path.join(patient_path, d)) if f.endswith('.dcm')]
            if dcm_files:
                ds = pydicom.dcmread(os.path.join(patient_path, d, dcm_files[0]))
                print(f"{count:4d} fichiers | {ds.Modality:4s} | {d[:50]}")
