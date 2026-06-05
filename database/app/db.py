import os
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import HTTPException


@contextmanager
def get_cursor():
    try:
        connection = psycopg2.connect(os.environ["DATABASE_URL"])
    except Exception as error:
        raise HTTPException(500, f"DB connection failed: {error}")
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            yield cursor
            connection.commit()
    finally:
        connection.close()
