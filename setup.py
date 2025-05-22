#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name="element_enhance",
    version="0.1.0",
    description="Enhanced UI operations for Browser-Use",
    author="Browser-Use Team",
    packages=find_packages(),
    install_requires=[
        "browser-use",
    ],
    python_requires=">=3.9",
) 