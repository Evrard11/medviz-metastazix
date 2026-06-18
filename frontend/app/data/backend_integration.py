"""
Version Docker-compatible : pas de téléchargement ni de segmentation au démarrage.
Fournit les mêmes variables (segmenter, lung_points, lung_polys) que la version
d'origine, mais sans dépendance au backend ML ni à internet.
Les vraies données viendront du backend via HTTP plus tard.
"""
import numpy as np


class FakeSegmenter:
    """Stub minimal pour que le frontend démarre seul."""
    def __init__(self, depth=128, h=512, w=512):
        self.lung = np.zeros((depth, h, w), dtype=np.int16)


segmenter = FakeSegmenter()

# Maillage 3D vide au démarrage
lung_points = []
lung_polys = []
