import sys
import os
from pathlib import Path

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if backend_path not in sys.path:
    sys.path.append(backend_path)

from backend.segmentation.downloader import LidcIdriDownloader
from backend.segmentation.patient_manager import PatientManager
from backend.segmentation.segmenter import Segmenter

# Configuration
data_dir = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../data/dicom')))
data_dir.mkdir(parents=True, exist_ok=True)
patient_id = "LIDC-IDRI-0001"

# Download
downloader = LidcIdriDownloader(data_dir, [patient_id])
downloader.download()

# Loading patient data
patient_manager = PatientManager(patient_id, downloader)
patient_manager.init()

# Segmentation
segmenter = Segmenter(patient_manager)
segmenter.preprocess()
segmenter.nodules_segmented = segmenter.segment_otsu()

print("Backend prêt.")
