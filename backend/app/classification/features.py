import numpy as np
import SimpleITK as sitk
from radiomics import featureextractor
from .masking import create_mask


def cube_to_sitk(cube: np.ndarray, spacing: tuple) -> sitk.Image:
    image = sitk.GetImageFromArray(cube.astype(np.float32))
    image.SetSpacing(spacing)
    return image

def extract_features(cube: np.ndarray, spacing: tuple, seg_mask: np.ndarray = None) -> dict:
    mask = create_mask(cube, seg_mask)

    # force mask size same as cube
    if mask.shape != cube.shape:
        min_z = min(mask.shape[0], cube.shape[0])
        min_y = min(mask.shape[1], cube.shape[1])
        min_x = min(mask.shape[2], cube.shape[2])
        mask = mask[:min_z, :min_y, :min_x]
        cube = cube[:min_z, :min_y, :min_x]

    if mask.sum() < 10:
        return {}

    image_sitk = cube_to_sitk(cube, spacing)
    mask_sitk = cube_to_sitk(mask.astype(np.float32), spacing)

    extractor = featureextractor.RadiomicsFeatureExtractor()
    extractor.disableAllFeatures()
    extractor.enableFeatureClassByName('shape') #shape
    extractor.enableFeatureClassByName('firstorder') #statistic
    extractor.enableFeatureClassByName('glcm') #texture

    result = extractor.execute(image_sitk, mask_sitk)

    # Only numerical login
    features = {}
    for key, val in result.items():
        if not key.startswith('diagnostics_'):
            features[key] = float(val)

    return features
