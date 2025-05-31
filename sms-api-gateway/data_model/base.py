"""
Base data model relating to utils, files, protocols, etc.
"""


import ast
from dataclasses import dataclass, asdict, Field, field
import datetime
import json
from types import FunctionType
from typing import Any, Callable, List, Dict, Optional, Union

import pandas as pd
from pydantic import ConfigDict, BaseModel as _BaseModel


class BaseModel(_BaseModel):
    """Base Pydantic Model with custom app configuration"""
    model_config = ConfigDict(arbitrary_types_allowed=True)


@dataclass
class BaseClass:
    @property
    def base_exception(self):
        return Exception(f"Cannot set a value as it is protected.")
    
    @classmethod
    def _stamp_factory(cls):
        return get_timestamp
    
    @classmethod
    def get_timestamp(cls):
        return BaseClass._stamp_factory()
    
    @property
    def timestamp(self):
        return BaseClass.get_timestamp()

    @timestamp.setter
    def timestamp(self, v):
        raise self.base_exception

    def dict(self):
        serialized = asdict(self)
        serialized['timestamp'] = self.timestamp
        return serialized
    
    def json(self):
        return json.dumps(self.dict())
    
    def dataframe(self):
        data = self.dict()
        indices = list(range(len(data)))
        return pd.DataFrame(data, index=indices)
    
    def to_dict(self):
        return self.dict()
    
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
    from data_model.base import BaseClass
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


@dataclass
class Node(BaseClass):
    data: Any 
    next: Any = None


class LinkedList:
    def __init__(self):
        self.head = None
        self.value = []

    # Method to add a node at the beginning of the LL
    def insertAtBegin(self, data):
        new_node = Node(data)
        new_node.next = self.head
        self.head = new_node
        self.value.insert(0, data)

    # Method to add a node at any index
    # Indexing starts from 0.
    def insertAtIndex(self, data, index):
        if index == 0:
            self.insertAtBegin(data)
            return

        position = 0
        current_node = self.head
        while current_node is not None and position + 1 != index:
            position += 1
            current_node = current_node.next

        if current_node is not None:
            new_node = Node(data)
            new_node.next = current_node.next
            current_node.next = new_node
        else:
            print("Index not present")
        self.value.insert(index, data)

    # Method to add a node at the end of LL
    def insertAtEnd(self, data):
        new_node = Node(data)
        self.value.append(data)
        if self.head is None:
            self.head = new_node
            return

        current_node = self.head
        while current_node.next:
            current_node = current_node.next

        current_node.next = new_node
        

    # Update node at a given position
    def updateNode(self, val, index):
        current_node = self.head
        position = 0
        while current_node is not None and position != index:
            position += 1
            current_node = current_node.next

        if current_node is not None:
            current_node.data = val
        else:
            print("Index not present")

    # Method to remove first node of linked list
    def remove_first_node(self):
        if self.head is None:
            return

        self.head = self.head.next

    # Method to remove last node of linked list
    def remove_last_node(self):
        if self.head is None:
            return

        # If there's only one node
        if self.head.next is None:
            self.head = None
            return

        # Traverse to the second last node
        current_node = self.head
        while current_node.next and current_node.next.next:
            current_node = current_node.next

        current_node.next = None

    # Method to remove a node at a given index
    def remove_at_index(self, index):
        if self.head is None:
            return

        if index == 0:
            self.remove_first_node()
            return

        current_node = self.head
        position = 0
        while current_node is not None and current_node.next is not None and position + 1 != index:
            position += 1
            current_node = current_node.next

        if current_node is not None and current_node.next is not None:
            current_node.next = current_node.next.next
        else:
            print("Index not present")

    # Method to remove a node from the linked list by its data
    def remove_node(self, data):
        current_node = self.head

        # If the node to be removed is the head node
        if current_node is not None and current_node.data == data:
            self.remove_first_node()
            return

        # Traverse and find the node with the matching data
        while current_node is not None and current_node.next is not None:
            if current_node.next.data == data:
                current_node.next = current_node.next.next
                return
            current_node = current_node.next

        # If the data was not found
        print("Node with the given data not found")

    # Print the size of the linked list
    def sizeOfLL(self):
        size = 0
        current_node = self.head
        while current_node:
            size += 1
            current_node = current_node.next
        return size

    # Print the linked list
    def printLL(self):
        current_node = self.head
        while current_node:
            print(current_node.data)
            current_node = current_node.next
    
    def __repr__(self) -> str:
        return str(self.value)


def test_linked_list():
    # create a new linked list
    llist = LinkedList()

    # add nodes to the linked list
    llist.insertAtEnd('a')
    llist.insertAtBegin('b')
    assert eval(repr(llist)) == ['b', 'a']