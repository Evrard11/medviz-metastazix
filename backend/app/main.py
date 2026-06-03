import os
from fastapi import FastAPI

app = FastAPI()

@app.get("/hello")
async def get_hello():
    return "hello world!"