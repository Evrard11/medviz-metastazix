from playwright.sync_api import Page, expect
from pathlib import Path

# helper function
def create_patient(page, name="Jean Dupont"):
    page.goto("http://localhost:80")
    page.click(".dash-debug-menu__toggle")
    page.click("#upload-dicom")
    page.wait_for_selector('input[type="file"]')
    page.set_input_files(
        'input[type="file"]',
        "data/LIDC-IDRI-0001.zip"
    )
    page.wait_for_selector("#patient-name-input")
    page.fill("#patient-name-input", name)
    page.click("#submit-patient-btn")
    page.wait_for_selector("#submit-patient-btn", state="hidden")

def test_patient_saved(page):
    create_patient(page)
    response = page.request.get("http://0.0.0.0:8001/patients")
    assert response.ok
    assert any(
        p["first_name"] == "Jean" and p["last_name"] == "Dupont"
        for p in response.json()
    )

def test_patient_appears_in_list(page):
    first_name, last_name = "Jean", "Dupont"
    create_patient(page, name=first_name+" "+last_name)
    expect(page.locator("#patients-list")).to_contain_text(f"{last_name}, {first_name}")

def test_exam_created(page):
    create_patient(page)
    response = page.request.get("http://0.0.0.0:8001/patients")
    patient = response.json()[-1]
    response = page.request.get(f"http://0.0.0.0:8001/patients/{patient['id']}/exams")
    assert response.ok
    assert len(response.json()) == 1

def test_segmentation_created(page):
    create_patient(page)
    patient = page.request.get("http://0.0.0.0:8001/patients").json()[-1]
    exam = page.request.get(f"http://0.0.0.0:8001/patients/{patient['id']}/exams").json()[0]
    response = page.request.get(f"http://0.0.0.0:8001/exams/{exam['id']}/segmentations")
    assert response.ok
    assert len(response.json()) == 1

def test_nodules_saved(page):
    create_patient(page)
    patient = page.request.get("http://0.0.0.0:8001/patients").json()[-1]
    exam = page.request.get(f"http://0.0.0.0:8001/patients/{patient['id']}/exams").json()[0]
    segmentation = page.request.get(f"http://0.0.0.0:8001/exams/{exam['id']}/segmentations").json()[0]
    response = page.request.get(f"http://0.0.0.0:8001/segmentations/{segmentation['id']}/nodules")
    assert response.ok
    assert len(response.json()) > 0

def test_switch_patient(page):
    create_patient(page, "Jean Dupont")
    create_patient(page, "Alice Martin")
    # get back on first patient
    page.get_by_text("Dupont, Jean").click()
    # callback should load back patient data
    expect(page.locator("#anomalies-list")).not_to_be_empty()

def test_open_medical_report(page):
    create_patient(page)
    page.wait_for_selector("#open-report-btn")
    page.click("#open-report-btn")
    expect(page.locator("#report-modal-body")).to_be_visible()
    expect(page.locator("#report-content")).to_contain_text("Rapport d'imagerie - Jean Dupont")
    expect(page.locator("#report-content")).to_contain_text("Conclusion Médicale")

def test_delete_anomaly(page):
    create_patient(page)
    delete_buttons = page.locator("[id*='delete-anomaly']")
    #expect(delete_buttons.first).to_be_visible()
    nb_before = delete_buttons.count()
    delete_buttons.first.click()
    expect(page.locator("[id*='delete-anomaly']")).to_have_count(nb_before - 1)

def test_patient_persistence_after_reload(page):
    create_patient(page, "Jean Dupont")
    page.reload()
    page.wait_for_selector("#patients-list")
    expect(page.locator("#patients-list")).to_contain_text("Dupont, Jean")
