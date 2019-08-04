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
Testing of the module manager commands

'''
import asynctest
import os
import shutil

from PaGS.managers import moduleManager
from PaGS.vehicle.vehicle import Vehicle
from PaGS.mavlink.pymavutil import getpymavlinkpackage


class ModuleManagerTest(asynctest.TestCase):

    """
    Class to test manager module commands
    """

    def setUp(self):
        """Set up some data that is reused in many tests"""

        self.manager = None

        # The PaGS settings dir (just in source dir)
        self.settingsdir = os.path.join(os.getcwd(), ".PaGS")
        if not os.path.exists(self.settingsdir):
            os.makedirs(self.settingsdir)

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
        self.VehA.hasInitial = True

        self.txPackets = {}
        self.txVehPackets = {}
        self.txPackets["VehA"] = []

        self.manager = moduleManager.moduleManager(self.loop, self.settingsdir, False)
        self.manager.onVehListAttach(self.getVehListCallback)
        self.manager.onVehGetAttach(self.getVehicleCallback)
        self.manager.onPktTxAttach(self.txcallback)

        self.manager.addModule("internalPrinterModule")

    async def tearDown(self):
        """Close down the test"""
        await self.VehA.stopheartbeat()
        await self.VehA.stoprxtimeout()
        if os.path.exists(self.settingsdir):
            shutil.rmtree(self.settingsdir)

    def vehSendFunc(self, buf, name):
        """Event for when vehicle send buffer"""
        self.txVehPackets[name] = buf

    def txcallback(self, name, pkt, **kwargs):
        """Event callback to sending a packet on to vehiclemanager"""
        self.txPackets[name].append(pkt)

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
        return self.manager.multiModules['internalPrinterModule'].printedout[Veh][line]

    def test_loadModule(self):
        """Test loading: good, bad and existing"""
        self.manager.onModuleCommandCallback(
            "VehA", "module load modules.dontexist")

        assert self.getOutText("VehA", 1) == "Cannot find module"
        assert len(self.manager.multiModules) == 1

        self.manager.onModuleCommandCallback(
            "VehA", "module load modules.modeModule")

        assert self.getOutText("VehA", 3) == "Loaded module modules.modeModule"
        assert len(self.manager.multiModules) == 2

        self.manager.onModuleCommandCallback(
            "VehA", "module load modules.modeModule")

        assert self.getOutText("VehA", 5) == "Module already loaded"
        assert len(self.manager.multiModules) == 2

    def test_listModule(self):
        """
        Test listing of modules "module list"
        """
        self.manager.onModuleCommandCallback(
            "VehA", "module list")

        assert self.getOutText("VehA", 1) == "Loaded Modules: "
        assert self.getOutText("VehA", 2) == "internalPrinterModule"

        self.manager.onModuleCommandCallback(
            "VehA", "module load modules.modeModule")
        self.manager.onModuleCommandCallback(
            "VehA", "module list")

        assert self.getOutText("VehA", 6) == "Loaded Modules: "
        assert self.getOutText("VehA", 7) == "internalPrinterModule"
        assert self.getOutText("VehA", 8) == "PaGS.modules.modeModule"


if __name__ == '__main__':
    asynctest.main()
