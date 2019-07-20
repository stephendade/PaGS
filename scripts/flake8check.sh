#!/bin/bash

flake8 ../PaGS --count --ignore=E501,E402,W504 --show-source --statistics --max-line-length=127
flake8 ../tests --count --ignore=E501,E402,W504 --show-source --statistics --max-line-length=127
