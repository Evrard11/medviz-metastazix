DO $$ BEGIN
    CREATE TYPE exam_status AS ENUM ('uploaded','processing','segmented','validated','error');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE algo_name AS ENUM ('kmeans','random_forest','xgboost','manual');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS patients (
    id            SERIAL PRIMARY KEY,
    anonymized_id VARCHAR(20) UNIQUE NOT NULL,
    first_name    VARCHAR(100),
    last_name     VARCHAR(100),
    birthdate     DATE,
    sex           CHAR(1) CHECK (sex IN ('M','F','O','U')),
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS exams (
    id              SERIAL PRIMARY KEY,
    patient_id      INT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    dicom_path      TEXT NOT NULL,
    date_exam       DATE NOT NULL,
    modality        VARCHAR(10) NOT NULL DEFAULT 'CT',
    slice_thickness NUMERIC(5,2),
    num_slices      INT,
    notes           TEXT,
    status          exam_status NOT NULL DEFAULT 'uploaded',
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS segmentations (
    id                SERIAL PRIMARY KEY,
    exam_id           INT NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    algorithm         algo_name NOT NULL,
    algorithm_version VARCHAR(20),
    parameters        JSONB,
    mask_path         TEXT,
    nodule_count      INT,
    is_validated      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS nodules (
    id              SERIAL PRIMARY KEY,
    segmentation_id INT NOT NULL REFERENCES segmentations(id) ON DELETE CASCADE,
    centroid_x      NUMERIC(8,2),
    centroid_y      NUMERIC(8,2),
    centroid_z      NUMERIC(8,2),
    volume_mm3      NUMERIC(10,2),
    max_diameter_mm NUMERIC(6,2),
    malignancy_score NUMERIC(4,3),
    tnm_category    VARCHAR(5),
    features        JSONB,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_exams_patient ON exams(patient_id);
CREATE INDEX IF NOT EXISTS idx_seg_exam      ON segmentations(exam_id);
CREATE INDEX IF NOT EXISTS idx_nodules_seg   ON nodules(segmentation_id);
