import sys
from pathlib import Path


def resolve():
    return sys.path.append(str(Path().resolve().parent))

