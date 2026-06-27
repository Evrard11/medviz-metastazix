import pydicom
import SimpleITK as sitk
import numpy as np
import matplotlib.pyplot as plt
import os
from .downloader import LidcIdriDownloader
from skimage.measure import label, regionprops

class PatientManager:
    """
    PatientManager class
    Extract volume + annotations from patient dicom directory
    """
    # volume format: (Z, Y, X)
    volume : np.ndarray = None
    seg_masks: list[np.ndarray] = None
    dicom_files = None
    seg_metas = None

    def __init__(self, pid="", dl: LidcIdriDownloader=None):
        if dl is None:
            self.patient_path = None
        else:
            self.patient_path = dl.get_patient_path(pid)

    def init(self, patient_path=None):
        if patient_path is not None:
            self.patient_path = patient_path
        ct_path = None
        seg_paths = []
        # Get CT and SEG files
        for d in os.listdir(self.patient_path):
            full_path = os.path.join(self.patient_path, d)
            if not os.path.isdir(full_path):
                continue
            dcm_files = [f for f in os.listdir(full_path) if f.endswith('.dcm')]
            if not dcm_files:
                continue
            ds = pydicom.dcmread(os.path.join(full_path, dcm_files[0]))
            if ds.Modality == 'CT' and len(dcm_files) > 10:
                ct_path = full_path
            elif ds.Modality == 'SEG':
                seg_paths.append(full_path)

        print(f"CT : {ct_path}")
        print(f"SEG : {len(seg_paths)} masks found")

        # load CT
        reader = sitk.ImageSeriesReader()
        self.dicom_names = reader.GetGDCMSeriesFileNames(ct_path)
        reader.SetFileNames(self.dicom_names)
        ct_image = reader.Execute()
        self.volume = sitk.GetArrayFromImage(ct_image)
        self.voxel_size = ct_image.GetSpacing()
        print(f"Voxel size : {self.voxel_size}")

        # load SEG
        self.seg_masks = []
        self.seg_metas = []
        for seg_path in seg_paths:
            seg_file = [f for f in os.listdir(seg_path) if f.endswith('.dcm')][0]
            seg_ds = pydicom.dcmread(os.path.join(seg_path, seg_file))
            seg_image = sitk.ReadImage(os.path.join(seg_path, seg_file))
            mask = sitk.GetArrayFromImage(seg_image)
            self.seg_masks.append(mask)
            self.seg_metas.append(seg_ds)

    def remap_seg_to_ct(self, id : int):
        """
        Replace SEG mask on volume
        :param id: i-th SEG
        :return: volume with annotations
        """
        seg_ds = self.seg_metas[id]
        seg_mask = self.seg_masks[id]

        # get z pos from SEG slices
        positions = []
        for i in range(len(seg_ds.PerFrameFunctionalGroupsSequence)):
            frame = seg_ds.PerFrameFunctionalGroupsSequence[i]
            z = float(frame.PlanePositionSequence[0].ImagePositionPatient[2])
            positions.append(z)

        # get z pos from CT
        ct_z = []
        for f in self.dicom_names:
            ds = pydicom.dcmread(f)
            ct_z.append(float(ds.ImagePositionPatient[2]))
        ct_z = np.array(ct_z)

        volume_mask = np.zeros(self.volume.shape, dtype=np.uint8)
        for i, z_pos in enumerate(positions):
            # find nearest CT slice
            idx = np.argmin(np.abs(ct_z - z_pos))
            volume_mask[idx] |= seg_mask[i]

        return volume_mask

    def get_volume_with_annotations(self):
        masks3D = []
        for i in range(len(self.seg_masks)):
            m = self.remap_seg_to_ct(i)
            slices = np.where(m.any(axis=(1,2)))[0]
            masks3D.append(m)

        # Merge masks
        annotations = np.any(masks3D, axis=0).astype(np.uint8)

        return annotations

    def display_volume_with_annotations(self):
        """DEBUG: Show all images with annotations"""
        annotations = self.get_volume_with_annotations()

        for z in range(self.volume.shape[0]):
            if annotations[z].any():
                plt.figure(figsize=(12, 5))
                plt.imshow(self.volume[z], cmap='gray', vmin=-1000, vmax=400)
                plt.imshow(annotations[z], alpha=0.4, cmap='Reds')
                plt.title(f"CT - tranche {z}")
                plt.axis('off')

                plt.tight_layout()
                plt.show()

    def get_annotation_candidates(self, patch_size=32) -> list[dict]:
        """
        Convert SEG annotations to candidate format (same as Segmenter.get_candidates)
        """
        annotations = self.get_volume_with_annotations()
        half = patch_size // 2

        lab = label(annotations)
        regions = regionprops(lab)

        candidates = []
        for r in regions:
            cz, cy, cx = (int(v) for v in r.centroid)
            cube = self.volume[
                max(0, cz - half):cz + half,
                max(0, cy - half):cy + half,
                max(0, cx - half):cx + half
            ]
            candidates.append({
                'cube': cube,
                'centroid': (cz, cy, cx),
                'bbox': r.bbox,
                'area': r.area,
                'spacing': self.voxel_size,
            })

        print(f"{len(candidates)} annotation candidates.")
        return candidates