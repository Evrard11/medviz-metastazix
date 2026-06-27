from pathlib import Path

import pytest
from app.segmentation.downloader import LidcIdriDownloader
from app.segmentation.patient_manager import PatientManager
from app.segmentation.segmenter import Segmenter

# tests only on nodule not GGO
PATIENT_IDS = [
    'LIDC-IDRI-0001', 'LIDC-IDRI-0003', 'LIDC-IDRI-0007', 'LIDC-IDRI-0009',
    'LIDC-IDRI-0011', 'LIDC-IDRI-0012', 'LIDC-IDRI-0015', 'LIDC-IDRI-0017',
    'LIDC-IDRI-0031', 'LIDC-IDRI-0033', 'LIDC-IDRI-0036', 'LIDC-IDRI-0037',
    'LIDC-IDRI-0042', 'LIDC-IDRI-0045', 'LIDC-IDRI-0046', 'LIDC-IDRI-0050',
    'LIDC-IDRI-0051', 'LIDC-IDRI-0053', 'LIDC-IDRI-0054', 'LIDC-IDRI-0059',
    'LIDC-IDRI-0060', 'LIDC-IDRI-0061', 'LIDC-IDRI-0063', 'LIDC-IDRI-0068',
    'LIDC-IDRI-0075', 'LIDC-IDRI-0079', 'LIDC-IDRI-0086', 'LIDC-IDRI-0089',
    'LIDC-IDRI-0097', 'LIDC-IDRI-0098',
]

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
def matches(patient, segmenter):
    annotations_mask = patient.get_volume_with_annotations()
    ann_candidates = patient.get_annotation_candidates()
    pairs = Segmenter.match_candidates(ann_candidates, segmenter.candidates)
    return dict(
        ann_candidates=ann_candidates,
        ann_mask=annotations_mask,
        pairs=pairs,
    )

