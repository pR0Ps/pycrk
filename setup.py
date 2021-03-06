#!/usr/bin/env python

from setuptools import setup

setup(
    name="pycrk",
    version="0.0.1",
    description="Applies/restores patches in *.crk files",
    url="https://github.com/pR0Ps/pycrk",
    license="MPLv2",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
    ],
    packages=["pycrk"],
    entry_points={"console_scripts": ["pycrk=pycrk.__main__:main"]},
)
