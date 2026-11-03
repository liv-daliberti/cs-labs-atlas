"""Packaging data lives in pyproject.toml; the flat modules of tools/ are discovered here so a new tool needs no packaging edit."""
from pathlib import Path

from setuptools import setup

setup(py_modules=sorted(p.stem for p in (Path(__file__).resolve().parent / 'tools').glob('*.py')))
