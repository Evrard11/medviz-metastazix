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

print("Génération du maillage 3D des poumons...")
import numpy as np
from skimage.measure import marching_cubes

downsampled_lung_mesh = segmenter.lung[::4, ::4, ::4]
verts, faces, _, _ = marching_cubes(downsampled_lung_mesh, level=-400)

verts = verts * 4

# Convert Z, Y, X to X, Y, Z
lung_points_arr = np.zeros_like(verts)
lung_points_arr[:, 0] = verts[:, 2]
lung_points_arr[:, 1] = verts[:, 1]
lung_points_arr[:, 2] = verts[:, 0]

lung_points = lung_points_arr.flatten().tolist()
lung_polys = np.column_stack((np.full(len(faces), 3), faces)).flatten().tolist()

print("Backend prêt.")
