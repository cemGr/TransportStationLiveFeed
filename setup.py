# setup.py
from setuptools import setup, find_packages


def parse_requirements(path: str) -> list[str]:
    """Return a list of requirements from the given requirements file."""
    requirements = []
    with open(path, encoding="utf-8") as req_file:
        for line in req_file:
            line = line.strip()
            if line and not line.startswith("#"):
                requirements.append(line)
    return requirements

setup(
    name="StationLiveFeed",
    version="0.1.0",
    packages=find_packages(),
    install_requires=parse_requirements("requirements.txt"),
)
