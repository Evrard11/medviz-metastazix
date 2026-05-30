from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from utils.sql_query import (
    open_connection,
    close_connection,
)

app = FastAPI()

@app.get("/hello")
async def get_hello():
    return "hello world!"

@app.get("/get-table")
async def get_database():
    connection, cursor = open_connection()

    # SQL queries can be written in utils/sql_query.py
    # cursor.execute("SELECT * FROM table;")
    # data = cursor.fetchall()

    close_connection(connection, cursor)
    return None  # data
