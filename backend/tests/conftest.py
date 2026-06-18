from pathlib import Path

import pytest
from segmentation.downloader import LidcIdriDownloader
from segmentation.patient_manager import PatientManager
from segmentation.segmenter import Segmenter

PATIENT_IDS = ['LIDC-IDRI-0001', 'LIDC-IDRI-0003']

ROOT = Path(__file__).parent.parent

@pytest.fixture(scope="session")
def dl():
    dl = LidcIdriDownloader(str(ROOT / "LIDC_data"), PATIENT_IDS)
    if all((ROOT / "LIDC_data" / pid).exists() for pid in PATIENT_IDS):
        dl.fill_patients_files_info()
    else:
        dl.download()
    return dl

@pytest.fixture(scope="session", params=PATIENT_IDS)
def patient(request, dl):
    p = PatientManager(request.param, dl)
    p.init()
    return p

@pytest.fixture(scope="session")
def segmenter(patient):
    seg = Segmenter(patient)
    seg.run()
    return seg

@pytest.fixture(scope="session")
def matching(patient, segmenter):
    annotations_mask = patient.get_volume_with_annotations()
    ann_candidates = patient.get_annotation_candidates()
    offset = segmenter.get_roi_offset()
    pairs = Segmenter.match_candidates(ann_candidates, segmenter.candidates, roi_offset=offset)
    return dict(
        ann_candidates=ann_candidates,
        annotations_mask=annotations_mask,
        pairs=pairs,
        offset=offset,
    )
