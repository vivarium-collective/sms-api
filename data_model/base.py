"""
Base data model relating to utils, files, protocols, etc.
"""


import ast
from dataclasses import dataclass, asdict, Field, field
import datetime
from types import FunctionType
from typing import Any, Callable, List, Dict, Optional, Union

from pydantic import ConfigDict, BaseModel as _BaseModel


class BaseModel(_BaseModel):
    """Base Pydantic Model with custom app configuration"""
    model_config = ConfigDict(arbitrary_types_allowed=True)


@dataclass
class BaseClass:
    @property
    def base_exception(self):
        return Exception(f"Cannot set a value as it is protected.")

    @property
    def _get_time(self):
        return get_timestamp

    @property
    def timestamp(self):
        return self._get_time()
    
    @timestamp.setter
    def timestamp(self, v):
        raise self.base_exception

    def to_dict(self):
        serialized = asdict(self)
        serialized['timestamp'] = self.timestamp
        return serialized
    
    @property
    def _attributes(self):
        serial = self.to_dict()
        return list(serial.keys())
    
    @property
    def attributes(self):
        return self._attributes

    @attributes.setter 
    def attributes(self, v):
        raise self.base_exception
    
    @property
    def _values(self):
        serial = self.to_dict()
        return list(serial.values())
    
    @property
    def values(self):
        return self._values

    @values.setter 
    def values(self, v):
        raise self.base_exception


def get_timestamp():
        return str(datetime.datetime.now())


def parse_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value
    elif isinstance(value, dict):
        return {k: parse_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [parse_value(v) for v in value]
    return value


@dataclass
class DynamicData:
    _params: Dict[str, Any]

    def __post_init__(self):
        cleaned = parse_value(self._params)
        for k, v in cleaned.items():
            setattr(self, k, v)


class EncodedKey(bytes):
    def __new__(cls, key: str, *args):
        return key.encode('utf-8')
    

def test_base_class():
    from dataclasses import dataclass as dc 
    from api.data_model.base import BaseClass
    @dc 
    class X(BaseClass):
        i: float
        j: float 
        def tuplize(self): return (self.i, self.j)
    
    success = False 
    x = X(11, 2.22)
    try:
        x.timestamp = "123"
    except:
        success = True 
    
    assert success
    return x