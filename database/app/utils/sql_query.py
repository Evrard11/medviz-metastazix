import psycopg2
import os
from fastapi import HTTPException
from pathlib import Path

SCHEMA_FILE = Path(__file__).parent.parent.parent/"db"/"01_schema.sql"

def open_connection():
    connection, cursor = None, None
    try:
        connection = psycopg2.connect(os.environ["DATABASE_URL"])
        cursor = connection.cursor()
    except Exception as error:
        raise HTTPException(
            status_code=400, detail=f"fail to connect to the database: {error}"
        )
    return connection, cursor

def close_connection(connection, cursor):
    cursor.close()
    connection.close()


def init_db():
    connection, cursor = open_connection()

    create_tables = SCHEMA_FILE.read_text()
    cursor.execute(create_tables)
    connection.commit()

    close_connection(connection, cursor)
