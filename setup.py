from setuptools import setup, find_packages

setup(
    name="fish-sim-reboot",
    version="0.5.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[line.strip() for line in open("requirements.txt") if line.strip() and not line.startswith("#")],
    python_requires=">=3.8",
)
