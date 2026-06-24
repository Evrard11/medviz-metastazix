import numpy as np

def create_mask(cube: np.ndarray, seg_mask: np.ndarray = None) -> np.ndarray:
    if seg_mask is not None and seg_mask.sum() > 0:
        return seg_mask.astype(np.uint8)

    mask = (cube >= -600) & (cube <= 400)
    return mask.astype(np.uint8)