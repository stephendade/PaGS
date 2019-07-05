============
Installation
============

PaGS is compatible with Python 3.5 - 3.7 on both Linux or Windows.

At the command line::

    git clone https://github.com/stephendade/PaGS.git
    cd ./PaGS
    pip install -U -r requirements.txt -r requirements_gui.txt
    python setup.py build install --user

If using a headless (no screen) system, omit the ``-r requirements_gui.txt`` section in the above.

If installing for development, the test dependencies can be installed by::

    pip install -U -r ./tests/requirements_test.txt