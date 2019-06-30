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
Testing of the "template" module

'''
import asyncio
import asynctest
import logging

from PaGS.managers import moduleManager
from PaGS.vehicle.vehicle import Vehicle
from PaGS.mavlink.pymavutil import getpymavlinkpackage

class ModuleManagerTest(asynctest.TestCase):

    """
    Class to test templateModule
    """

    def setUp(self):
        """Set up some data that is reused in many tests"""

        self.manager = None

        self.dialect = 'ardupilotmega'
        self.version = 2.0
        self.mod = getpymavlinkpackage(self.dialect, self.version)
        self.mavUAS = self.mod.MAVLink(
            self, srcSystem=4, srcComponent=0, use_native=False)
        self.VehA = Vehicle(self.loop, "VehA", 255, 0, 4, 0, self.dialect, self.version)

        self.txPackets = {}

    async def tearDown(self):
        """Close down the test"""
        await self.VehA.stopheartbeat()
        await self.VehA.stoprxtimeout()

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
        self.manager = moduleManager.moduleManager(self.loop, self.dialect, self.version, False)
        self.manager.onVehListAttach(self.getVehListCallback)
        self.manager.onVehGetAttach(self.getVehicleCallback)

        self.manager.addModule("PaGS.modules.templateModule")

        # is the module loaded?
        assert len(self.manager.multiModules) == 1
        assert "template" in self.manager.commands
        assert len(self.manager.commands["template"]) == 2

        self.manager.removeModule("PaGS.modules.templateModule")

        # is the module unloaded?
        assert len(self.manager.multiModules) == 0
        assert "template" not in self.manager.commands

    def test_cmd_do_stuff(self):
        """Test the do_stuff() command"""
        self.manager = moduleManager.moduleManager(self.loop, self.dialect, self.version, False)
        self.manager.onVehListAttach(self.getVehListCallback)
        self.manager.onVehGetAttach(self.getVehicleCallback)

        self.manager.addModule("PaGS.modules.templateModule")

        # execute a command
        self.manager.onModuleCommandCallback("VehA", "template do_stuff 1 \"the rest\"")

        # and assert
        assert self.manager.multiModules['PaGS.modules.templateModule'].calledStuff["VehA"] == "1,the rest"

    def test_incoming(self):
        """Test incoming packets"""
        pass

if __name__ == '__main__':
    asynctest.main()
