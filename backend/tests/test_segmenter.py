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
        assert any(iou_score > 0.1 for iou_score in iou_scores), f"{iou_scores} != 0.1"