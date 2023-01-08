#!/usr/bin/env python

from setuptools import setup

setup(
    name="pycrk",
    version="0.0.1",
    description="Applies/restores patches in *.crk files",
    url="https://github.com/pR0Ps/pycrk",
    license="MPLv2",
    py_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    packages=["pycrk"],
    entry_points={"console_scripts": [
        "crk-apply=pycrk.__main__:apply_crk",
        "crk-generate=pycrk.__main__:generate_crk",
    ]},
)
