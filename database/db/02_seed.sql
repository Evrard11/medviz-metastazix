INSERT INTO patients (anonymized_id, first_name, last_name, birthdate, sex) VALUES
('PAT_00001', 'Jean',  'Dupont', '1955-03-12', 'M'),
('PAT_00002', 'Marie', 'Martin', '1962-07-28', 'F');

INSERT INTO exams (patient_id, dicom_path, date_exam, slice_thickness, num_slices, status) VALUES
(1, '/storage/dicom/1/1/', '2026-01-15', 1.25, 256, 'segmented'),
(2, '/storage/dicom/2/2/', '2026-02-10', 1.00, 320, 'uploaded');

INSERT INTO segmentations (exam_id, algorithm, algorithm_version, parameters, mask_path, nodule_count, is_validated) VALUES
(1, 'kmeans', '1.0', '{"k": 3}'::jsonb, '/storage/masks/1.nii.gz', 2, TRUE);

INSERT INTO nodules (segmentation_id, centroid_x, centroid_y, centroid_z, volume_mm3, max_diameter_mm, tnm_category) VALUES
(1, 145.5, 220.3, 80.1, 720.30, 12.4, 'T1b'),
(1, 200.1, 180.5, 120.4, 525.20, 10.8, 'T1b');
