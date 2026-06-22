import uuid

try:
    from repositories import patient_repository, exam_repository, segmentation_repository, nodule_repository

except ImportError:
    from app.repositories import patient_repository, exam_repository, segmentation_repository, nodule_repository

def _uid(prefix="REPO"):
    return f"{prefix}_{str(uuid.uuid4())[:8]}"



def test_patient_create_get():
    data = {"anonymized_id": _uid(), "first_name": "Repo", "last_name": "Test", "birthdate": None, "sex": "F"}
    created = patient_repository.create(data)
    assert created["id"] is not None, "pas d'id"
    fetched = patient_repository.get_by_id(created["id"])
    assert fetched["anonymized_id"] == data["anonymized_id"], "anonymized_id différent"
    print(f"OK test_patient_create_get — id {created['id']}")


def test_patient_update():
    created = patient_repository.create({"anonymized_id": _uid(), "first_name": None,
                                         "last_name": None, "birthdate": None, "sex": None})
    updated = patient_repository.update(created["id"], {"first_name": "Modifié"})
    assert updated["first_name"] == "Modifié", "update échoué"
    print("OK test_patient_update")


def test_patient_delete():
    created = patient_repository.create({"anonymized_id": _uid(), "first_name": None,
                                         "last_name": None, "birthdate": None, "sex": None})
    deleted = patient_repository.delete(created["id"])
    assert deleted is not None, "delete a échoué"
    assert patient_repository.get_by_id(created["id"]) is None, "patient toujours présent"
    print("OK test_patient_delete")


def test_patient_list():
    result = patient_repository.list_all(limit=10, offset=0)
    assert isinstance(result, list), "devrait être une liste"
    print(f"OK test_patient_list — {len(result)} patients")



def test_exam_create_and_link():
    patient = patient_repository.create({"anonymized_id": _uid(), "first_name": None,
                                         "last_name": None, "birthdate": None, "sex": None})
    exam = exam_repository.create(patient["id"], {
        "dicom_path": "/storage/dicom/test/", "date_exam": "2026-01-15", "modality": "CT",
        "slice_thickness": None, "num_slices": None, "notes": None, "status": "uploaded",
    })
    assert exam["patient_id"] == patient["id"], "patient_id incorrect"
    fetched = exam_repository.get_by_id(exam["id"])
    assert fetched is not None, "exam introuvable"
    print(f"OK test_exam_create_and_link — id {exam['id']}")


def test_exam_update_status():
    patient = patient_repository.create({"anonymized_id": _uid(), "first_name": None,
                                         "last_name": None, "birthdate": None, "sex": None})
    exam = exam_repository.create(patient["id"], {
        "dicom_path": "/x/", "date_exam": "2026-01-15", "modality": "CT",
        "slice_thickness": None, "num_slices": None, "notes": None, "status": "uploaded",
    })
    updated = exam_repository.update(exam["id"], {"status": "segmented"})
    assert updated["status"] == "segmented", "status pas mis à jour"
    print("OK test_exam_update_status")



def test_segmentation_and_nodule():
    patient = patient_repository.create({"anonymized_id": _uid(), "first_name": None,
                                         "last_name": None, "birthdate": None, "sex": None})
    exam = exam_repository.create(patient["id"], {
        "dicom_path": "/x/", "date_exam": "2026-01-15", "modality": "CT",
        "slice_thickness": None, "num_slices": None, "notes": None, "status": "uploaded",
    })
    seg = segmentation_repository.create(exam["id"], {
        "algorithm": "kmeans", "algorithm_version": "1.0", "parameters": {"k": 3},
        "mask_path": None, "nodule_count": 1, "is_validated": False,
    })
    assert seg["algorithm"] == "kmeans", "algorithme incorrect"

    nod = nodule_repository.create(seg["id"], {
        "centroid_x": 1.0, "centroid_y": 2.0, "centroid_z": 3.0,
        "volume_mm3": None, "max_diameter_mm": None, "malignancy_score": 0.5,
        "tnm_category": "T1a", "features": None,
    })
    assert nod["malignancy_score"] == 0.5, "score incorrect"
    print("OK test_segmentation_and_nodule")


def test_cascade_delete():
    """Supprimer le patient supprime exam → segmentation → nodule (ON DELETE CASCADE)."""
    patient = patient_repository.create({"anonymized_id": _uid(), "first_name": None,
                                         "last_name": None, "birthdate": None, "sex": None})
    exam = exam_repository.create(patient["id"], {
        "dicom_path": "/x/", "date_exam": "2026-01-15", "modality": "CT",
        "slice_thickness": None, "num_slices": None, "notes": None, "status": "uploaded",
    })
    seg = segmentation_repository.create(exam["id"], {
        "algorithm": "kmeans", "algorithm_version": None, "parameters": None,
        "mask_path": None, "nodule_count": None, "is_validated": False,
    })
    nodule_repository.create(seg["id"], {
        "centroid_x": 1.0, "centroid_y": 2.0, "centroid_z": 3.0,
        "volume_mm3": None, "max_diameter_mm": None, "malignancy_score": None,
        "tnm_category": None, "features": None,
    })

    patient_repository.delete(patient["id"])
    assert exam_repository.get_by_id(exam["id"]) is None, "exam pas supprimé en cascade"
    assert segmentation_repository.get_by_id(seg["id"]) is None, "segmentation pas supprimée en cascade"
    print("OK test_cascade_delete")


if __name__ == "__main__":
    tests = [
        test_patient_create_get,
        test_patient_update,
        test_patient_delete,
        test_patient_list,
        test_exam_create_and_link,
        test_exam_update_status,
        test_segmentation_and_nodule,
        test_cascade_delete,
    ]
    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL {t.__name__} — {e}")
            failed += 1
    print(f"\n{passed}/{passed + failed} tests repositories passés")
