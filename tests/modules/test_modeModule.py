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
Testing of the "mode" module

'''

import asynctest
import asyncio

from PaGS.managers import moduleManager
from PaGS.vehicle.vehicle import Vehicle
from PaGS.mavlink.pymavutil import getpymavlinkpackage


class ModeModuleTest(asynctest.TestCase):

    """
    Class to test Mode module
    """

    def setUp(self):
        """Set up some data that is reused in many tests"""

        self.manager = None

        self.dialect = 'ardupilotmega'
        self.version = 2.0
        self.mod = getpymavlinkpackage(self.dialect, self.version)
        self.mavUAS = self.mod.MAVLink(
            self, srcSystem=4, srcComponent=0, use_native=False)
        self.VehA = Vehicle(self.loop, "VehA", 255, 0, 4,
                            0, self.dialect, self.version)
        self.VehA.onPacketTxAttach(self.vehSendFunc)
        self.VehA.vehType = 1
        self.VehA.fcName = 3

        self.txPackets = {}
        self.txVehPackets = {}

        self.manager = moduleManager.moduleManager(self.loop, False)
        self.manager.onVehListAttach(self.getVehListCallback)
        self.manager.onVehGetAttach(self.getVehicleCallback)
        self.manager.onPktTxAttach(self.txcallback)

        self.manager.addModule("PaGS.modules.internalPrinterModule")

    async def tearDown(self):
        """Close down the test"""
        await self.VehA.stopheartbeat()
        await self.VehA.stoprxtimeout()

    def vehSendFunc(self, buf, name):
        """Event for when vehicle send buffer"""
        self.txVehPackets[name] = buf

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

    def getOutText(self, Veh: str, line: int):
        """Helper function for getting output text from internalPrinterModule"""
        return self.manager.multiModules['PaGS.modules.internalPrinterModule'].printedout[Veh][line]

    def test_loadModule(self):
        """Test adding and removal of module"""
        self.manager.addModule("PaGS.modules.modeModule")

        # is the module loaded?
        assert len(self.manager.multiModules) == 2
        assert "mode" in self.manager.commands
        assert len(self.manager.commands["mode"]) == 2

        self.manager.removeModule("PaGS.modules.modeModule")

        # is the module unloaded?
        assert len(self.manager.multiModules) == 1
        assert "mode" not in self.manager.commands

    def test_cmd_listmodes(self):
        """Test the listModes() command"""
        self.manager.addModule("PaGS.modules.modeModule")

        # execute a command
        self.manager.onModuleCommandCallback(
            "VehA", "mode list")

        # and assert
        assert self.getOutText("VehA", 1)[0:18] == "Valid modes are: ["
        assert self.getOutText("VehA", 1)[-1] == "]"

    def test_cmd_doMode(self):
        """Test the doMode command"""
        self.manager.addModule("PaGS.modules.modeModule")

        # execute a bad mode
        self.manager.onModuleCommandCallback(
            "VehA", "mode do BADMODE")

        # assert
        assert len(self.txPackets) == 0
        assert self.getOutText("VehA", 1) == "No mode: BADMODE"

        # execute a mode change
        self.manager.onModuleCommandCallback(
            "VehA", "mode do AUTO")

        # assert
        assert len(self.txPackets) == 1

    def test_incoming(self):
        """Test incoming packets"""
        pass


if __name__ == '__main__':
    asynctest.main()
