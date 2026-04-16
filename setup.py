import os
from setuptools import setup, find_packages

def read_requirements():
    """Parse requirements.txt, filtering out comments and empty lines."""
    requirements_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
    with open(requirements_file) as f:
        return [
            line.strip() 
            for line in f 
            if line.strip() and not line.strip().startswith("#")
        ]

setup(
    name="fish-sim-reboot",
    version="0.5.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=read_requirements(),
    python_requires=">=3.8",
)
