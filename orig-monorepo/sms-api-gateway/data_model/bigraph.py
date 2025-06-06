"""
Data Model relating to Bigraph (process-bigraph) specification: nodes, composites, etc.
"""


import os
from dataclasses import dataclass, Field
from typing import List, Dict, Any


class NodeSpec(dict):
    def __init__(self, _type: str, address: str, config: Dict[str, Any], inputs: Dict[str, List[str]], outputs: Dict[str, List[str]], name: str = None):
        super().__init__()
        self._type = _type
        self.address = address
        self.config = config
        self.inputs = inputs
        self.outputs = outputs
        self.name = name


def node_spec(_type: str, address: str, config: Dict[str, Any], inputs: Dict[str, List[str]], outputs: Dict[str, List[str]], name: str = None) -> Dict[str, Any]:
    spec = {
        '_type': _type,
        'address': address,
        'config': config,
        'inputs': inputs,
        'outputs': outputs
    }

    return {name: spec} if name else spec


def step_node_spec(address: str, config: Dict[str, Any], inputs: Dict[str, Any], outputs: Dict[str, Any], name: str = None):
    return node_spec(name=name, _type="step", address=address, config=config, inputs=inputs, outputs=outputs)


def process_node_spec(address: str, config: Dict[str, Any], inputs: Dict[str, Any], outputs: Dict[str, Any], name: str = None):
    return node_spec(name=name, _type="process", address=address, config=config, inputs=inputs, outputs=outputs)


def time_course_node_spec(input_file: str, context: str, start_time: int, end_time: int, num_steps: int):
    config = {
        'input_file': input_file,
        'start_time': start_time,
        'end_time': end_time,
        'num_steps': num_steps,
        'context': context
    }
    return step_node_spec(
        address='local:time-course-output-generator',
        config=config,
        inputs={
            'parameters': [f'parameters_store_{context}']
        },
        outputs={
            'output_data': [f'output_data_store_{context}']
        }
    )
