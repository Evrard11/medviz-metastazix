import os
import xml.etree.ElementTree as ET
import numpy as np

NS = "http://www.nih.gov"  # LIDC XML namespace

def find_xml_for_series(xml_dir, series_uid):
    # walk through all XML files and return the one matching the series UID
    for root_dir, dirs, files in os.walk(xml_dir):
        for fname in files:
            if not fname.endswith(".xml"):
                continue
            path = os.path.join(root_dir, fname)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if series_uid in content:
                return path
    return None

def parse_nodules(xml_path):
    # parse nodule contours and malignancy scores from all reading sessions
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # collect scores and ROIs per nodule ID across all radiologists
    nodule_scores = {}
    nodule_rois = {}

    for session in root.findall(f"{{{NS}}}readingSession"):
        for nodule in session.findall(f"{{{NS}}}unblindedReadNodule"):
            nid = nodule.find(f"{{{NS}}}noduleID").text.strip()

            # malignancy (only present on nodules >= 3mm)
            chars = nodule.find(f"{{{NS}}}characteristics")
            if chars is not None:
                mal = chars.find(f"{{{NS}}}malignancy")
                if mal is not None:
                    nodule_scores.setdefault(nid, []).append(int(mal.text.strip()))

            # contours: one ROI per slice
            for roi in nodule.findall(f"{{{NS}}}roi"):
                z = float(roi.find(f"{{{NS}}}imageZposition").text.strip())
                points = [
                    (int(e.find(f"{{{NS}}}xCoord").text),
                     int(e.find(f"{{{NS}}}yCoord").text))
                    for e in roi.findall(f"{{{NS}}}edgeMap")
                ]
                nodule_rois.setdefault(nid, []).append({"z": z, "points": points})

    # only keep nodules with a malignancy score
    result = []
    for nid, scores in nodule_scores.items():
        result.append({
            "nodule_id": nid,
            "malignancy": np.mean(scores),
            "rois": nodule_rois.get(nid, []),
        })

    return result

def build_mask_from_rois(rois, volume_shape, ct_z_positions):
    from skimage.draw import polygon
    ct_z = np.array(ct_z_positions)
    mask = np.zeros(volume_shape, dtype=np.uint8)

    for roi in rois:
        # find nearest CT slice
        idx = np.argmin(np.abs(ct_z - roi["z"]))
        if not roi["points"]:
            continue
        xs = np.array([p[0] for p in roi["points"]])
        ys = np.array([p[1] for p in roi["points"]])
        # fill polygon interior
        rr, cc = polygon(ys, xs, shape=volume_shape[1:])
        mask[idx, rr, cc] = 1

    return mask

def extract_cube(volume, mask, patch_size=32):
    # find nodule centroid from mask
    coords = np.argwhere(mask == 1)
    if len(coords) == 0:
        return None, None
    cz, cy, cx = coords.mean(axis=0).astype(int)

    half = patch_size // 2
    # extract cube centered on centroid
    cube = volume[
        max(0, cz - half):cz + half,
        max(0, cy - half):cy + half,
        max(0, cx - half):cx + half
    ]
    return cube, (cz, cy, cx)