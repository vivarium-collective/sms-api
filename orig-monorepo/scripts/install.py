# install_subprojects.py
import subprocess
from pathlib import Path


def find_pyproject_packages(root):
    packages = []
    for path in Path(root).rglob("pyproject.toml"):
        if ".venv" not in path.parts and "site-packages" not in path.parts:
            packages.append(str(path.parent.resolve()))
    return packages


def install_packages(packages):
    for pkg in packages:
        print(f"Installing: {pkg}")
        subprocess.run(["uv", "pip", "install", "-e", pkg], check=True)


if __name__ == "__main__":
    roots = [
        "/Users/alexanderpatrie/Desktop/repos/ecoli/genEcoli",
        "/Users/alexanderpatrie/Desktop/repos/spatio-flux",
        "/Users/alexanderpatrie/Desktop/repos/ecoli/vEcoli",
    ]
    for root in roots:
        packages = find_pyproject_packages(root)
        install_packages(packages)
