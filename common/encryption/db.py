import base64
from hashlib import sha256
import os
from os import getcwd
import pickle
import sqlite3
import gzip
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from vivarium.vivarium import Vivarium


load_dotenv()


def make_test_password(viv_id: str):
    return sha256(viv_id.encode('utf-8')).hexdigest()


def salt(size: int = 16):
    return os.urandom(size)


def key_creation(password: bytes, salt: bytes, n_iterations: int = 600_000):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        salt=salt,
        iterations=1024,
        length=32,
        backend=default_backend(),
    )
    key = Fernet(base64.urlsafe_b64encode(kdf.derive(password)))
    return key


def encryption(b, pswd):
    s = salt()
    f = key_creation(pswd, s)
    safe = f.encrypt(b)
    return s + safe


def decryption(safe: bytes | str, pswd):
    s = safe[:16]  # get prepended salt
    f = key_creation(pswd, s)
    b = f.decrypt(safe[16:])
    return b


def open_cdb(name: str, pswd: bytes):
    f = gzip.open(getcwd() + name + '_crypted.sql.gz', 'rb')  # TODO: make this safer.
    safe: bytes | str = f.read()
    f.close()
    content = decryption(safe, pswd)
    content = content.decode('utf-8')
    con = sqlite3.connect(':memory:')
    con.executescript(content)
    return con


def save_cdb(con, name, pswd: bytes):
    fp = gzip.open(getcwd() + name + '_crypted.sql.gz', 'wb')
    b = b''
    for line in con.iterdump():
        b += bytes('%s\n', 'utf8') % bytes(line, 'utf8')
    b = encryption(b, pswd)
    fp.write(b)
    fp.close()


def pickle_vivarium(v: Vivarium, vivarium_id: str) -> Path:
    pickled_viv = pickle.dumps(v)
    temp_dir = tempfile.mkdtemp()
    tmp_pickle_path = os.path.join(temp_dir, f"{vivarium_id}.pckl")
    
    with open(tmp_pickle_path, "wb") as f:
        f.write(pickled_viv)

    del pickled_viv
    
    return Path(tmp_pickle_path)


def write(instance: Vivarium, vivarium_id: str, pswd: bytes, table_name: str = "pickles") -> None:
    # pickle instance
    pickle_path: Path = pickle_vivarium(instance, vivarium_id)
    with open(pickle_path, "rb") as f:
        data = f.read()

    # store to in-memory db
    conn = sqlite3.connect(':memory:')
    cur = conn.cursor()
    cur.execute(f"CREATE TABLE {table_name} (id TEXT PRIMARY KEY, data BLOB)")
    cur.execute(f"INSERT INTO {table_name} VALUES (?, ?)", (vivarium_id, data))

    # encrypt and save to db via cdb
    save_cdb(conn, table_name, pswd)
    del data
    conn.close()


def read(pswd: bytes, vivarium_id: str, table_name: str = "pickles") -> Vivarium:
    # connect and decrypt db
    conn = open_cdb(table_name, pswd)
    cursor = conn.execute(
        f"SELECT data FROM {table_name} WHERE id = ?", (vivarium_id,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise ValueError(f"No Vivarium with id '{vivarium_id}' found.")

    return pickle.loads(row[0])


def list_ids(pswd: bytes, table_name: str = "pickles") -> list[str]:
    """Lists all stored vivarium pickles by their ids"""
    conn = open_cdb(table_name, pswd)
    cursor = conn.execute(f"SELECT id FROM {table_name}")
    ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return ids





