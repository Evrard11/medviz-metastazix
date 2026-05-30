import psycopg2
import os
from fastapi import HTTPException

def open_connection():
    connection, cursor = None, None
    try:
        connection = psycopg2.connect(os.environ["DATABASE_URL"])
        cursor = connection.cursor()
    except Exception as error:
        raise HTTPException(
            status_code=400, detail=f"fail to connect to the database: {error}"
        )

    create_default_table(connection, cursor)
    return connection, cursor


def close_connection(connection, cursor):
    cursor.close()
    connection.close()
