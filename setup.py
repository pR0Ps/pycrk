#!/usr/bin/env python

from setuptools import setup
import os.path


try:
    DIR = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(DIR, "README.md"), encoding='utf-8') as f:
        long_description = f.read()
except Exception:
    long_description=None


setup(
    name="pycrk",
    version="0.0.1",
    description="Applies/restores patches in *.crk files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pR0Ps/pycrk",
    license="MPLv2",
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: Utilities",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
    ],
    packages=["pycrk"],
    entry_points={"console_scripts": [
        "crk-apply=pycrk.__main__:apply_crk",
        "crk-generate=pycrk.__main__:generate_crk",
    ]},
)
