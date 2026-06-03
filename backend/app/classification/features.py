import numpy as np
import SimpleITK as sitk
from radiomics import featureextractor

def cube_to_sitk(cube: np.ndarray, spacing: tuple) -> sitk.Image:
    image = sitk.GetImageFromArray(cube.astype(np.float32))
    image.SetSpacing(spacing)
    return image

def extract_features(cube: np.ndarray, spacing: tuple) -> dict:
    from masking import create_mask
    mask = create_mask(cube)

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