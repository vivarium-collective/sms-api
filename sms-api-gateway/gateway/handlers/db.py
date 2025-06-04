import json
import sqlite3

from typing import List, Any

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase


SIMDATA_ROW_SCHEMA = {
    "experiment_id": "TEXT PRIMARY KEY",
    "data": "TEXT"
}
DATABASE_DIR = "databases"
DEFAULT_SIMDATA_DB_PATH = f"{DATABASE_DIR}/simdata.db"


def connection(db_path: str = DEFAULT_SIMDATA_DB_PATH):
    return sqlite3.connect(db_path)


def write(tablename: str, payload: dict[str, dict], conn: sqlite3.Connection):
    """
    Inserts a JSON payload into the specified SQLite table.

    Args:
        tablename (str): The table to insert into.
        payload (dict[str, dict]): A dictionary where each key is a unique ID or name,
                                   and each value is a dictionary of data to store.
        conn (sqlite3.Connection): Active SQLite connection.

    Returns:
        sqlite3.Connection: The same connection, after insertions.
    """
    cursor = conn.cursor()

    # Ensure the table exists and has the right schema
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {tablename} (
            experiment_id TEXT PRIMARY KEY,
            data TEXT
        )
    ''')

    # Insert each item from the payload
    for key, data in payload.items():
        json_str = json.dumps(data)
        cursor.execute(
            f"INSERT OR REPLACE INTO {tablename} (experiment_id, data) VALUES (?, ?)",
            (key, json_str)
        )

    conn.commit()
    return conn


def read(tablename: str, columns: list[str], filters: dict[str, Any], db_path: str = DEFAULT_SIMDATA_DB_PATH):
    """
    Query a SQLite table with specified columns and filter conditions.

    Args:
        tablename (str): Name of the table to query.
        columns (List[str]): List of columns to select.
        filters (Dict[str, Any]): Filters in the form of column: value.
        db_path (str): Path to the SQLite database file.

    Returns:
        List[tuple]: List of query result rows.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    column_str = ", ".join(columns)
    filter_str = " AND ".join(f"{k} = ?" for k in filters)
    values = tuple(filters.values())

    query = f"SELECT {column_str} FROM {tablename} WHERE {filter_str};"
    cursor.execute(query, values)
    results = cursor.fetchall()

    conn.close()
    return results


def test_insert():
    conn = sqlite3.connect("test.db")
    payload = {
        "experiment1": {"temperature": 37, "pH": 7.2},
        "experiment2": {"temperature": 25, "pH": 6.8},
    }

    write("experiments", payload, conn)


def configure_mongo():
    MONGO_URI = "mongodb://localhost:27017/"
    client = AsyncMongoClient(MONGO_URI)
    db: AsyncDatabase = client.get_database("simulations")
    return client, db 
