import numpy as np

def create_mask(cube: np.ndarray) -> np.ndarray:
    mask_array = np.zeros(cube.shape)
    mask = (cube > -100) & (cube < 400)
    mask_array[mask] = 1
    return mask_array