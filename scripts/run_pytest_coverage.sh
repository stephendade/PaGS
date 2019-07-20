#!/bin/bash

cd ../
python3 setup.py build install --user
python3 -m pytest --log-level DEBUG --cov=PaGS
