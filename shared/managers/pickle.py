import abc
from pathlib import Path
import shutil
import pickle
import os
import dataclasses as dc
import sqlite3

import tempfile as tf
from vivarium.vivarium import Vivarium


class BasePickler(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def read(cls, viv_id: str) -> Vivarium:
        pass
    
    @classmethod
    @abc.abstractmethod
    def write(cls, viv: Vivarium, viv_id: str):
        pass


class Pickler(BasePickler):
    @classmethod
    def read(cls, local_pickle_path: Path) -> Vivarium:
        with open(local_pickle_path, 'rb') as f:
            data = pickle.load(f)
        return data
    
    @classmethod
    def write(cls, viv: Vivarium, viv_id: str) -> Path:
        p = pickle.dumps(viv)
        tmp = tf.mkdtemp()
        path = Path(os.path.join(tmp, f'{viv_id}.pckl'))
        with open(path, 'wb') as fp:
            fp.write(p)
        return path


class DatabasePickler(BasePickler):
    @classmethod
    def get_db_path(cls):
        return "pickles.db"
    
    @classmethod
    def read(cls, vivarium_id: str) -> Vivarium:
        with sqlite3.connect(cls.get_db_path()) as conn:
            cur = conn.cursor()
            cur.execute("SELECT data FROM pickles WHERE id = ?", (vivarium_id,))
            row = cur.fetchone()
            cur.execute("SELECT id FROM pickles")
            print("Available IDs:", cur.fetchall())

            if row:
                viv = pickle.loads(row[0])
                print(f'Got viv: {viv}')
                return viv
            else:
                print("Pickle not found!")
                return Vivarium()
            
    @classmethod
    def write(cls, local_pickle_fp: str, vivarium_id: str):
        with open(local_pickle_fp, "rb") as f:
            data = f.read()
        
        with sqlite3.connect(cls.get_db_path()) as conn:
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS pickles (id TEXT PRIMARY KEY, data BLOB)")
            cur.execute("INSERT OR REPLACE INTO pickles (id, data) VALUES (?, ?)", (vivarium_id, data))
            conn.commit()
