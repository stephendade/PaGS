============
Introduction
============

PAGS (Python-async Ground Station) is a ground station software suite for [MAVLink-based](https://mavlink.io/en/) autonomous vehicles, including [Ardupilot](http://ardupilot.org/) based vehicles.

It is inspired by the [MAVProxy](http://ardupilot.github.io/MAVProxy/html/index.html) GCS, and features a similar module-based architecture.

The "async" comes from PAGS being entirely based on the asyncio library in Python. This allows for efficient asynchonous processing between the modules and links.

It is designed from the ground up as modular and multi-vehicle.

General Features:

- Can run in a terminal or GUI
- Can be used as a GCS, or as the foundation of your own GCS
- Compatible with Python 3.5+ on Windows or Linux
- Any number of vehicles can be connected to a single PAGS instance
- Low number of dependencies
- Module can be quickly and easily developed for additional functionality
- Full CI testing with high test coverage

.. note::
   PAGS is still an early work in progress. Many features expected of a GCS are not currently present.

   .. toctree::
   :maxdepth: 2

   installation
   usage
   contributing
   development
   authors
   changelog
   reference/index