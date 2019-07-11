# PaGS

## Build Status

### Windows

OS | Python 3.5 | Python 3.6 | Python 3.7 |
|-------------------|-------------------|-------------------|-------------------|
Windows | [![build3][]][build-link] | [![build2][]][build-link] | [![build1][]][build-link] |
Linux | [![build4][]][build-link] | [![build5][]][build-link] | [![build6][]][build-link] |

[build1]: https://appveyor-matrix-badges.herokuapp.com/repos/stephendade/PaGS/branch/master/1
[build2]: https://appveyor-matrix-badges.herokuapp.com/repos/stephendade/PaGS/branch/master/2
[build3]: https://appveyor-matrix-badges.herokuapp.com/repos/stephendade/PaGS/branch/master/3
[build4]: https://appveyor-matrix-badges.herokuapp.com/repos/stephendade/PaGS/branch/master/4
[build5]: https://appveyor-matrix-badges.herokuapp.com/repos/stephendade/PaGS/branch/master/5
[build6]: https://appveyor-matrix-badges.herokuapp.com/repos/stephendade/PaGS/branch/master/6
[build-link]: https://ci.appveyor.com/project/stephendade/PaGS

[![Documentation Status](https://readthedocs.org/projects/pags/badge/?version=latest)](https://pags.readthedocs.io/en/latest/?badge=latest)
[![Requirements Status](https://requires.io/github/stephendade/PaGS/requirements.svg?branch=master)](https://requires.io/github/stephendade/PaGS/requirements/?branch=master)
[![Coverage Status](https://coveralls.io/repos/github/stephendade/PaGS/badge.svg?branch=master)](https://coveralls.io/github/stephendade/PaGS?branch=master)

## Introduction

PAGS (Python-async Ground Station) is a ground station software suite for [MAVLink-based](https://mavlink.io/en/) autonomous vehicles, including [Ardupilot](http://ardupilot.org/) based vehicles.

It is inspired by the [MAVProxy](http://ardupilot.github.io/MAVProxy/html/index.html) GCS, and features a similar module-based architecture.

The "async" comes from PAGS being entirely based on the asyncio library in Python. This allows for efficient asynchonous processing between the modules and links.

It is designed from the ground up as modular and multi-vehicle.

Documentation is at https://PaGS.readthedocs.io/

