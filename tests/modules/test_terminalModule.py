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

'''
Testing of the "terminal" module

'''

import asynctest
import pytest
import os
import shutil

from PaGS.managers import moduleManager
from PaGS.vehicle.vehicle import Vehicle
from PaGS.mavlink.pymavutil import getpymavlinkpackage


class TerminalModuleTest(asynctest.TestCase):

    """
    Class to test terminalModule
    """

    def setUp(self):
        """Set up some data that is reused in many tests"""

        self.dialect = 'ardupilotmega'
        self.version = 2.0
        self.mod = getpymavlinkpackage(self.dialect, self.version)
        self.mavUAS = self.mod.MAVLink(
            self, srcSystem=4, srcComponent=0, use_native=False)
        self.VehA = Vehicle(self.loop, "VehA", 255, 0, 4,
                            0, self.dialect, self.version)
        # The PaGS settings dir (just in source dir)
        self.settingsdir = os.path.join(os.getcwd(), ".PaGS")
        if not os.path.exists(self.settingsdir):
            os.makedirs(self.settingsdir)

        self.manager = moduleManager.moduleManager(self.loop, self.settingsdir, False)
        self.manager.onVehListAttach(self.getVehListCallback)
        self.manager.onVehGetAttach(self.getVehicleCallback)

        self.txPackets = {}

    async def tearDown(self):
        """Close down the test"""
        await self.VehA.stopheartbeat()
        await self.VehA.stoprxtimeout()
        if os.path.exists(self.settingsdir):
            shutil.rmtree(self.settingsdir)

    def txcallback(self, name, pkt, **kwargs):
        """Event callback to sending a packet on to vehiclemanager"""
        self.txPackets[name] = pkt

    def getVehListCallback(self):
        """Get list of vehicles"""
        return ["VehA"]

    def getVehicleCallback(self, vehname):
        """Get a particular vehicle"""
        if vehname == "VehA":
            return self.VehA
        else:
            raise ValueError('No vehicle with that name')

    def test_loadModule(self):
        """Test adding and removal of module"""

        # won't load in pytest, instead we just watch for the correct exception
        with pytest.raises(Exception) as excinfo:
            self.manager.addModule("PaGS.modules.terminalModule")

        # Appveyor doesn't have a console to display on
        if excinfo:
            assert "No module with that name" in str(excinfo.value)

    def test_incoming(self):
        """Test incoming packets"""
        pass


if __name__ == '__main__':
    asynctest.main()
