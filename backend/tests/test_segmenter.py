from segmentation.segmenter import Segmenter

class TestSegmenter:
    def test_recall(self, matching):
        pairs = matching['pairs']
        ann_candidates = matching['ann_candidates']
        recall = len(pairs) / len(ann_candidates)
        assert recall == 1., f"{len(ann_candidates) - len(pairs)} annotations unmatched"

    def test_iou(self, matching, segmenter):
        iou_scores = [
            Segmenter.compute_iou_3d(ann, cand, matching['annotations_mask'], segmenter.nodules_segmented, matching['offset'])
            for ann, cand in matching['pairs']
        ]
        for i, score in enumerate(iou_scores):
            assert score > 0.1, f"Pair {i} : IoU {score:.3f} <= 0.1"