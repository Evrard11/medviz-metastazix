import numpy as np

def create_mask(cube: np.ndarray) -> np.ndarray:
    mask = (cube >= -100) & (cube <= 400)
    return mask.astype(np.uint8)