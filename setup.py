"""Setup script for drudid package.

This is a minimal setup.py for compatibility.
The main configuration is in pyproject.toml.
"""

from setuptools import setup, find_packages

setup(
    name="drudid",
    packages=find_packages(),
    python_requires=">=3.10",
)
