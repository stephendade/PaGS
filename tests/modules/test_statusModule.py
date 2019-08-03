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
Testing of the "statusModule" module

'''

import asyncio
import asynctest
import os
import shutil

from PaGS.managers import moduleManager
from PaGS.vehicle.vehicle import Vehicle
from PaGS.mavlink.pymavutil import getpymavlinkpackage


class StatusModuleTest(asynctest.TestCase):

    """
    Class to test statusModule
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
        self.VehA.hasInitial = True

        # The PaGS settings dir (just in source dir)
        self.settingsdir = os.path.join(os.getcwd(), ".PaGS")
        if not os.path.exists(self.settingsdir):
            os.makedirs(self.settingsdir)

        self.manager = moduleManager.moduleManager(self.loop, self.settingsdir, False)
        self.manager.onVehListAttach(self.getVehListCallback)
        self.manager.onVehGetAttach(self.getVehicleCallback)
        self.manager.onPktTxAttach(self.txcallback)

        self.manager.addModule("internalPrinterModule")

    async def tearDown(self):
        """Close down the test"""
        await self.VehA.stopheartbeat()
        await self.VehA.stoprxtimeout()
        if "PaGS.modules.statusModule" in self.manager.multiModules:
            await self.manager.removeModule("PaGS.modules.statusModule")
        if os.path.exists(self.settingsdir):
            shutil.rmtree(self.settingsdir)

    def vehSendFunc(self, buf, name):
        """Event for when vehicle send buffer"""
        pass

    def txcallback(self, name, pkt, **kwargs):
        """Event callback to sending a packet on to vehiclemanager"""
        pass

    def getVehListCallback(self):
        """Get list of vehicles"""
        return ["VehA"]

    def getVehicleCallback(self, vehname):
        """Get a particular vehicle"""
        if vehname == "VehA":
            return self.VehA
        else:
            raise ValueError('No vehicle with that name')

    async def test_loadModule(self):
        """Test adding and removal of module"""
        self.manager.addModule("PaGS.modules.statusModule")

        # is the module loaded?
        # (noting that internalPrinter is already loaded)
        assert len(self.manager.multiModules) == 2
        assert "status" in self.manager.commands
        assert len(self.manager.commands["status"]) == 1

        await self.manager.removeModule("PaGS.modules.statusModule")

        # is the module unloaded?
        assert len(self.manager.multiModules) == 1
        assert "status" not in self.manager.commands

    async def test_cmd_status(self):
        """Test the "show" command"""
        self.manager.addModule("PaGS.modules.statusModule")

        # test with no params
        self.manager.onModuleCommandCallback("VehA", "status status")

        # assert
        assert self.getOutText("VehA", 1) == "No status packets recieved yet"

        # now there's a status packet at vehicle
        self.VehA.latestPacketDict["SYS_STATUS"] = self.mod.MAVLink_sys_status_message(
            52485167, 35684399, 52461871, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        # test with no params
        self.manager.onModuleCommandCallback("VehA", "status status")

        # assert
        assert self.getOutText("VehA", 3) == "3D_GYRO: Healthy"
        assert self.getOutText("VehA", 4) == "3D_ACCEL: Healthy"
        assert self.getOutText("VehA", 5) == "3D_MAG: Healthy"

    async def test_guiStart(self):
        """Simple test of the GUI startup"""

        # need to reset for handling gui
        self.manager = moduleManager.moduleManager(self.loop, self.settingsdir, True)
        self.manager.onVehListAttach(self.getVehListCallback)
        self.manager.onVehGetAttach(self.getVehicleCallback)
        self.manager.onPktTxAttach(self.txcallback)

        self.manager.addModule("internalPrinterModule")

        self.manager.addModule("PaGS.modules.statusModule")

        # Wait for param gui to load
        await asyncio.sleep(0.2)

        # Update the GUI with some status
        pkt = self.mod.MAVLink_sys_status_message(
            52485167, 35684399, 52461871, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        self.manager.multiModules["PaGS.modules.statusModule"].incomingPacket("VehA", pkt)

        # TODO: some GUI tests?

    def getOutText(self, Veh: str, line: int):
        """Helper function for getting output text from internalPrinterModule"""
        return self.manager.multiModules['internalPrinterModule'].printedout[Veh][line]


if __name__ == '__main__':
    asynctest.main()
