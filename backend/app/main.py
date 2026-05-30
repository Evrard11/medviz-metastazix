import os
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

DATABASE_BACKEND_URL = os.environ.get("DATABASE_BACKEND_URL", "")

app = FastAPI()

@app.get("/hello")
async def get_hello():
    return "hello world!"
