from app.segmentation.segmenter import Segmenter


class TestSegmenter:
    def test_recall(self, matches):
        pairs = matches['pairs']
        ann_candidates = matches['ann_candidates']
        recall = len(pairs) / len(ann_candidates)
        assert recall == 1., f"{len(pairs)} / {len(ann_candidates)} annotations unmatched"

    def test_iou(self, matches, segmenter):
        iou_scores = [
            Segmenter.compute_iou_3d(ann, cand, matches['ann_mask'], segmenter.nodules_mask)
            for ann, cand in matches['pairs']
        ]
        for i, score in enumerate(iou_scores):
            assert score > 0.1, f"Pair {i} : IoU {score:.3f} <= 0.1"
