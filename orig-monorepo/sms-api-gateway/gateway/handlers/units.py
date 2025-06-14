"""
Units: Extends the Unum units package.

TODO: Unum is a defunct project. Its source repo is no longer online. Either
switch to a newer package like Pint or copy and improve the Unum source code
from its Python package.
"""

from typing import TypeGuard

import numpy as np
import scipy.constants
from unum import Unum
from unum.units import *  # noqa: F403

# noinspection PyUnresolvedReferences
from unum.units import J, K, L, dmol, fg, g, h, min, mmol, mol, s, umol  # noqa: F401

count = Unum.unit("count", mol / scipy.constants.Avogadro)
nt = Unum.unit("nucleotide", count)
aa = Unum.unit("amino_acid", count)


def __truediv__(self, other):
    """Replacement Unum method that truly implements true division."""
    other = Unum.coerceToUnum(other)
    if not other._unit:
        unit = self._unit
    else:
        unit = self._unit.copy()
        for u, exp in list(other._unit.items()):
            exp -= unit.get(u, 0)
            if exp:
                unit[u] = -exp
            else:
                del unit[u]
    return Unum(unit, self._value / other._value)


def __rtruediv__(self, other):
    return Unum.coerceToUnum(other).__truediv__(self)


# Allow boolean testing on all Unum objects
def __bool__(self):
    return bool(self._value)


Unum.__bool__ = Unum.__nonzero__ = __bool__

# #244 workaround: Monkey patch Unum if it still has the broken implementation.
# The test also ensures this only patches it once.
# For some reason, `is` won't work here.
# See also https://github.com/CovertLab/wcEcoli/issues/433
if Unum.__truediv__ == Unum.__div__:
    Unum.__truediv__ = __truediv__
    Unum.__rtruediv__ = __rtruediv__


# noinspection PyShadowingBuiltins
def sum(array, axis=None, dtype=None, out=None, keepdims=False):
    if not isinstance(array, Unum):
        raise Exception("Only works on Unum!")

    units = getUnit(array)
    return units * np.sum(array.asNumber(), axis, dtype, out, keepdims)


# noinspection PyShadowingBuiltins
def abs(array):
    if not isinstance(array, Unum):
        raise Exception("Only works on Unum!")

    units = getUnit(array)
    return units * np.abs(array.asNumber())


def dot(a, b, out=None):
    if not isinstance(a, Unum):
        a_units = 1
    else:
        a_units = getUnit(a)
        a = a.asNumber()

    if not isinstance(b, Unum):
        b_units = 1
    else:
        b_units = getUnit(b)
        b = b.asNumber()

    return a_units * b_units * np.dot(a, b, out)


def matmul(a, b, out=None):
    if not isinstance(a, Unum):
        a_units = 1
    else:
        a_units = getUnit(a)
        a = a.asNumber()

    if not isinstance(b, Unum):
        b_units = 1
    else:
        b_units = getUnit(b)
        b = b.asNumber()

    return a_units * b_units * np.matmul(a, b, out)


Unum.__matmul__ = matmul


def multiply(a, b):
    if not isinstance(a, Unum):
        a_units = 1
    else:
        a_units = getUnit(a)
        a = a.asNumber()

    if not isinstance(b, Unum):
        b_units = 1
    else:
        b_units = getUnit(b)
        b = b.asNumber()

    return a_units * b_units * np.multiply(a, b)


def divide(a, b):
    if not isinstance(a, Unum):
        a_units = 1
    else:
        a_units = getUnit(a)
        a = a.asNumber()

    if not isinstance(b, Unum):
        b_units = 1
    else:
        b_units = getUnit(b)
        b = b.asNumber()

    return a_units / b_units * np.divide(a, b)


def floor(x):
    if not hasUnit(x):
        raise Exception("Only works on Unum!")
    x_unit = getUnit(x)
    x = x.asNumber()
    return x_unit * np.floor(x)


def transpose(array, axis=None):
    units = getUnit(array)

    return units * np.transpose(array.asNumber(), axis)


def hstack(tup):
    unit = getUnit(tup[0])
    value = []
    for array in tup:
        if not isinstance(array, Unum):
            raise Exception("Only works on Unum!")
        else:
            array.normalize()
            value.append(array.matchUnits(unit)[0].asNumber())
    value = tuple(value)
    return unit * np.hstack(value)


def getUnit(value):
    if not hasUnit(value):
        raise Exception("Only works on Unum!")

    value.normalize()
    value_units = value.copy()
    value_units._value = 1
    return value_units


def hasUnit(value) -> TypeGuard[Unum]:
    return isinstance(value, Unum)


def strip_empty_units(value):
    if hasUnit(value):
        value.normalize()
        value.checkNoUnit()
        value = value.asNumber()
    return value


def isnan(value):
    return np.isnan(value._value) if hasUnit(value) else np.isnan(value)


def isfinite(value):
    return np.isfinite(value._value) if hasUnit(value) else np.isfinite(value)
