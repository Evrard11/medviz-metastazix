from fastapi import FastAPI
from app.routers import patients, exams, segmentations, nodules

app = FastAPI(title="MedViz Database Service")

app.include_router(patients.router)
app.include_router(exams.router)
app.include_router(segmentations.router)
app.include_router(nodules.router)


@app.get("/health")
def health():
    return {"status": "ok"}
