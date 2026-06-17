import numpy as np
from scipy import ndimage
import matplotlib.pyplot as plt

from segmentation.patient_manager import PatientManager
from skimage.filters import threshold_otsu
from skimage.measure import label, regionprops
import SimpleITK as sitk

class Segmenter:

    def __init__(self, patient: PatientManager):
        self.patient = patient
        # mask of wall lung
        self.total_lung_mask = None
        # only lung part, derived from patient.volume
        self.lung = None
        # only lung part, derived from total_lung_mask
        self.lung_mask = None
        # area containing potentials nodules
        self.nodules_segmented = None
        # list of cubes containing potential nodule
        self.candidates = None

    # region Preprocess

    def extract_lung_mask(self, threshold=-400, dilation_it=3, erosion_it=5):
        """
        :param threshold: −350 HU, src => https://pmc.ncbi.nlm.nih.gov/articles/PMC12290796/
        :param dilation_it:
        :param erosion_it:
        :return:
        """
        thr_vol = self.patient.volume < threshold

        # Set lung outside to 0
        labeled, _ = ndimage.label(thr_vol)
        out_label = labeled[0, 0, 0]
        thr_vol[labeled == out_label] = 0

        # fill holes slice per slice
        filled = np.zeros_like(thr_vol)
        for z in range(thr_vol.shape[0]):
            filled[z] = ndimage.binary_fill_holes(thr_vol[z])

        # Only keep 2 lung 0_o
        labels, n2 = ndimage.label(filled)
        sizes = ndimage.sum(filled, labels, range(1, n2 + 1))
        big2_labels = np.argsort(sizes)[-2:] + 1
        lung_mask = np.isin(labels, big2_labels)

        # Dilatation to get pleural nodule (on wall lung)
        lung_mask = ndimage.binary_dilation(lung_mask, iterations=dilation_it)
        lung_mask = ndimage.binary_erosion(lung_mask, iterations=erosion_it)

        return lung_mask.astype(np.uint8)

    def get_lung_roi(self):
        """
        Resize volume + lung mask to fit focus more on lung
        """
        masked = self.patient.volume.copy()
        masked[self.total_lung_mask == 0] = -1000

        z_idx, y_idx, x_idx = np.where(self.total_lung_mask)
        lung = masked[
            z_idx.min():z_idx.max() + 1,
            y_idx.min():y_idx.max() + 1,
            x_idx.min():x_idx.max() + 1
        ]
        lung_mask = self.total_lung_mask[
            z_idx.min():z_idx.max() + 1,
            y_idx.min():y_idx.max() + 1,
            x_idx.min():x_idx.max() + 1
        ]
        print(f"volume shape: {self.patient.volume.shape}   |   lung shape: {lung.shape} ")
        return lung, lung_mask

    def preprocess(self):
        self.total_lung_mask = self.extract_lung_mask()

        self.lung, self.lung_mask = self.get_lung_roi()

    # endregion Preprocess

    # region Segmentation

    def segment_otsu(self):
        """
        Nice work on big objects
        :return:
        """
        # get threshold from otsu
        bool_roi = self.lung[self.lung_mask == 1]
        thr = threshold_otsu(bool_roi)

        candidates = (self.lung > thr) & (self.lung_mask == 1)

        # Erode to break connexions with wall lung
        eroded = ndimage.binary_erosion(candidates, iterations=2)

        lab = label(eroded)
        regions = regionprops(lab)

        nodule_mask = np.zeros_like(candidates, dtype=np.uint8)
        for r in regions:
            # too small => vessel, too big => trachea
            if 50 < r.area < 10000:
                nodule_mask[lab == r.label] = 1

        print(f"{len(regions)} composants otsu")
        return nodule_mask

    def segment_region_growing(self, lower=-100, upper=400):
        """
        Nice work on small objects
        :param lower:
        :param upper:
        :return:
        """

        sitk_img = sitk.GetImageFromArray(self.lung.astype(np.float32))

        seeds_mask = (self.lung > lower) & (self.lung_mask == 1)
        lab_seeds = label(seeds_mask)
        seed_regions = regionprops(lab_seeds)

        seeds_sitk = []
        for r in seed_regions:
            coords = r.coords
            values = self.lung[coords[:, 0], coords[:, 1], coords[:, 2]]
            best = coords[np.argmax(values)]
            seeds_sitk.append((int(best[2]), int(best[1]), int(best[0])))

        seg = sitk.ConnectedThreshold(
            sitk_img,
            seedList=seeds_sitk,
            lower=float(lower),
            upper=float(upper)
        )

        nodule_mask = sitk.GetArrayFromImage(seg).astype(np.uint8)
        nodule_mask = nodule_mask & self.lung_mask

        lab = label(nodule_mask)
        res = np.zeros_like(nodule_mask)
        for r in regionprops(lab):
            if 50 < r.area < 10000:
                res[lab == r.label] = 1

        print(f"{len(regionprops(label(res)))} composants region growing")
        return res

    def merge_nodules_segmented(self, mask1, mask2):
        return np.logical_or(mask1, mask2).astype(np.uint8)

    # endregion Segmentation

    # region Candidates

    def get_candidates(self, patch_size=32):
        """
        Create a list of cube center on composant
        :param patch_size:
        :return:
        """
        lab = label(self.nodules_segmented)
        regions = regionprops(lab)

        candidates = []
        for r in regions:
            cz, cy, cx = r.centroid

            half = patch_size // 2
            cz, cy, cx = int(cz), int(cy), int(cx)

            # Sub-volume
            cube = self.lung[
                max(0, cz - half):cz + half,
                max(0, cy - half):cy + half,
                max(0, cx - half):cx + half
            ]

            candidates.append({
                'cube': cube,
                'centroid': (cz, cy, cx),
                'bbox': r.bbox,
                'area': r.area,
                'spacing': self.patient.voxel_size,
            })

        self.candidates = candidates
        print(f"{len(candidates)} candidates.")

    def run(self):
        print("Preprocessing ...")
        self.preprocess()

        print("Segmentation ...")
        print("Otsu segmentation ...")
        nodules_segmented_ostu = self.segment_otsu()
        print("Region growing segmentation ...")
        nodules_segmented_rg = self.segment_region_growing()
        self.nodules_segmented = self.merge_nodules_segmented(nodules_segmented_ostu, nodules_segmented_rg)

        print("Selecting Candidates ...")
        self.get_candidates()

        return self.candidates

    # endregion Candidates

    # region Display

    def _to_roi_slice(self, slice_idx):
        """offset due to slices reduction"""
        z_offset = np.where(self.total_lung_mask)[0].min()
        return slice_idx - z_offset

    def display_lung_mask(self, slice_idx):
        """DEBUG: display lung mask"""
        plt.figure(figsize=(6, 6))
        plt.imshow(self.patient.volume[slice_idx], cmap='gray', vmin=-1000, vmax=400)
        plt.imshow(self.total_lung_mask[slice_idx], alpha=0.3, cmap='Greens')
        plt.title(f"Masque pulmonaire - tranche {slice_idx}")
        plt.show()

    def display_roi(self, slice_idx):
        """DEBUG: display roi slice"""
        roi_slice = self._to_roi_slice(slice_idx)
        plt.figure(figsize=(6, 6))
        plt.imshow(self.lung[roi_slice], cmap='gray', vmin=-1000, vmax=400)
        plt.title(f"Slice {slice_idx} (roi idx {roi_slice})")
        plt.show()

    def display_segmentation(self, slice_idx):
        """DEBUG: display segmentation slice"""
        roi_slice = self._to_roi_slice(slice_idx)
        plt.figure(figsize=(6, 6))
        plt.imshow(self.lung[roi_slice], cmap='gray', vmin=-1000, vmax=400)
        plt.imshow(self.nodules_segmented[roi_slice], alpha=0.4, cmap='Reds')
        plt.title(f"Segmentation - tranche {slice_idx} (roi idx {roi_slice})")
        plt.show()

    def display_segmentation_all(self):
        """DEBUG: display all slices with segmentation"""
        z_offset = np.where(self.total_lung_mask)[0].min()
        for roi_slice in range(self.lung.shape[0]):
            if not self.nodules_segmented[roi_slice].any():
                continue
            plt.figure(figsize=(6, 6))
            plt.imshow(self.lung[roi_slice], cmap='gray', vmin=-1000, vmax=400)
            plt.imshow(self.nodules_segmented[roi_slice], alpha=0.4, cmap='Reds')
            plt.title(f"Segmentation - roi idx {roi_slice} (volume idx {roi_slice + z_offset})")
            plt.show()

    def display_candidates_3d(self, max_display=10):
        """DEBUG: display lung candidates"""
        fig = plt.figure(figsize=(15, 5))
        n = min(len(self.candidates), max_display)

        for i, c in enumerate(self.candidates[:max_display]):
            ax = fig.add_subplot(1, n, i + 1, projection='3d')

            cz, cy, cx = c['centroid']
            half = 16

            # Extract cube
            patch_mask = self.nodules_segmented[
                max(0, cz - half):cz + half,
                max(0, cy - half):cy + half,
                max(0, cx - half):cx + half
            ]

            z, y, x = np.where(patch_mask > 0)
            ax.scatter(x, y, z, c='red', s=2, alpha=0.6)
            ax.set_title(f"#{i}\n{c['area']:.0f} vox")
            ax.axis('off')

        plt.tight_layout()
        plt.show()

    # endregion Display
