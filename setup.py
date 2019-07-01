#!/usr/bin/env python3
"""
The Python-async Ground Station (PaGS), a mavlink ground station for
autonomous vehicles.
Copyright (C) 2019  Stephen Dade

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import setuptools

setuptools.setup(
    name="PaGS",
    version="0.0.1",
    author="Stephen Dade",
    author_email="stephen_dade@hotmail.com",
    description="Python-async Ground Station. A mavlink based multivehicle ground station",
    url="https://github.com/stephendade/PaGS",
    zip_safe=True,
    packages=setuptools.find_packages(),
    scripts=["PaGS/pags.py"],
    install_requires=["pymavlink", "prompt-toolkit", "pyserial-asyncio"],
    tests_require=["pytest", "asynctest", "pytest-cov"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering",
        "Development Status :: 1 - Planning",
    ],
)
