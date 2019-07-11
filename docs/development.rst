============
Development
============

Installing
----------

See the :doc:`./installation` section

Testing and CI
--------------

All tests are in the ``./tests`` folder.

Windows users will need the `com0com <https://github.com/stephendade/PaGS/raw/master/tests/support/setup_com0com_W7_x64_signed.exe>`_ software.

Linux users will need socat installed via `sudo apt install socat``

Tests can be run via::

    python setup.py build install --user
    py.test --log-level DEBUG

The CI uses `Appveyor <https://ci.appveyor.com/project/stephendade/PaGS>`_ to run a build matrix of Windows/Linux and Python 3.5/3.6/3.7. So 6 runs total.

`Coveralls <https://coveralls.io/github/stephendade/PaGS?branch=master>`_ is used to check the test coverage.

Modules
-------
Modules must be placed in the ``./PaGS/PaGS/modules`` folder

There is a template available at ``./PaGS/PaGS/modules/blankModule.py``, or see below::

    """
    <Module Description>
    """

    class Module():
        """
        <Module Description>
        """
        def __init__(self, loop, txClbk, vehListClk, vehObjClk, cmdProcessClk, prntr, isGUI):
            self.txCallback = txClbk
            self.vehListCallback = vehListClk
            self.vehObjCallback = vehObjClk

            self.shortName = ""
            self.commandDict = {}

        def addVehicle(self, name: str):
            pass

        def incomingPacket(self, vehname: str, pkt):
            pass

        def removeVehicle(self, name: str):
            pass

        def closeModule(self):
            pass

If modules have a GUI, they should respect the isGUI parameter. They should use the wxPython (with wxAsync) GUI library for consistency.
For saving/loading window position and sizes, use the wxPersisent class:
<example of both>

Modules are free to set/get attributes in the vehicle classes, but they should not assume they are present.

Any commonly used vehicle attributes should be managed from within the vehicle class - parameters, waypoints, etc.

PAGS has a common cache/user setting directory at <>. It can be accessed from the <> attribute.

Each vehicle has it's own directory <accessed via the .. attribute>, where per vehicle files go - logs, parameter and waypoint files.

Each module should, where practical, test it's functionality within the unit test suite.

