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
import os
import shutil

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

    async def test_loadModule(self):
        """Test adding and removal of module"""
        self.manager.addModule("PaGS.modules.modeModule")

        # is the module loaded?
        assert len(self.manager.multiModules) == 2
        assert "mode" in self.manager.commands
        assert len(self.manager.commands["mode"]) == 5

        await self.manager.removeModule("PaGS.modules.modeModule")

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
        assert len(self.txPackets["VehA"]) == 0
        assert self.getOutText("VehA", 1) == "No mode: BADMODE"

        # execute a mode change
        self.manager.onModuleCommandCallback(
            "VehA", "mode do AUTO")

        # assert
        assert len(self.txPackets["VehA"]) == 1
        assert len(self.txPackets) == 1

    async def test_cmd_armDisarm(self):
        """Test the arm and disarm commands"""
        self.manager.addModule("PaGS.modules.modeModule")

        # execute an arm
        self.manager.onModuleCommandCallback(
            "VehA", "mode arm")

        # assert
        assert len(self.txPackets["VehA"]) == 1

        # execute a disarm
        self.manager.onModuleCommandCallback(
            "VehA", "mode disarm")

        # assert
        assert len(self.txPackets["VehA"]) == 2
        assert len(self.txPackets) == 1

    async def test_cmd_reboot(self):
        """Test the reboot command"""
        self.manager.addModule("PaGS.modules.modeModule")

        # execute an arm
        self.manager.onModuleCommandCallback(
            "VehA", "mode reboot")

        # assert
        assert len(self.txPackets["VehA"]) == 1

    def test_incoming(self):
        """Test incoming packets"""
        self.manager.addModule("PaGS.modules.modeModule")

        # change mode
        pkt = self.mod.MAVLink_heartbeat_message(
            self.mod.MAV_TYPE_QUADROTOR, self.mod.MAV_AUTOPILOT_ARDUPILOTMEGA, 0, 0, 4, int(self.version))
        self.manager.incomingPacket("VehA", pkt, "Constr")

        # assert
        assert self.getOutText("VehA", 0) == "Mode changed to: STABILIZE"

        # Don't change mode
        self.manager.incomingPacket("VehA", pkt, "Constr")

        # assert no extra text
        assert len(self.manager.multiModules['internalPrinterModule'].printedout["VehA"]) == 1


if __name__ == '__main__':
    asynctest.main()
