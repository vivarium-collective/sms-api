"""
Data model relating to quantum data in Qiskit and Cirq.
"""


from bsp.data_model.base import BaseClass
import numpy as np
from dataclasses import dataclass


class DiracNotation(np.ndarray):
    def __new__(cls, values: list[complex]):
        return np.asarray(values).view(cls)


class Bra(DiracNotation):
    pass


class Ket(DiracNotation):
    def bra(self) -> Bra:
        ket_value = self.view()
        return Bra(np.conj(ket_value).T)


class XYZMolecule(str):
    def __new__(cls, *args, **kwargs):
        return str.__new__(cls, *args, **kwargs)

    @property
    def elements(self, unique: bool = False) -> list:
        items = self.split()
        elements = [line[0] for line in [ln.strip() for ln in self.split(";")]]
        return list(set(elements)) if unique else elements


class MoleculeAtom:
    pass


