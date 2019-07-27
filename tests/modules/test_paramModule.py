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
Testing of the "paramModule" module

'''

import asyncio
import asynctest
import os
import shutil

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
        self.VehA = Vehicle(self.loop, "VehA", 255, 0, 4,
                            0, self.dialect, self.version)
        self.VehA.onPacketTxAttach(self.vehSendFunc)
        self.VehA.hasInitial = True

        # The PaGS settings dir (just in source dir)
        self.settingsdir = os.path.join(os.getcwd(), ".PaGS")
        if not os.path.exists(self.settingsdir):
            os.makedirs(self.settingsdir)

        self.txPackets = {}
        self.txVehPackets = {}

        self.manager = moduleManager.moduleManager(self.loop, self.settingsdir, False)
        self.manager.onVehListAttach(self.getVehListCallback)
        self.manager.onVehGetAttach(self.getVehicleCallback)
        self.manager.onPktTxAttach(self.txcallback)

        self.manager.addModule("PaGS.modules.internalPrinterModule")

    async def tearDown(self):
        """Close down the test"""
        await self.VehA.stopheartbeat()
        await self.VehA.stoprxtimeout()
        if "PaGS.modules.paramModule" in self.manager.multiModules:
            await self.manager.removeModule("PaGS.modules.paramModule")
        if os.path.exists(self.settingsdir):
            shutil.rmtree(self.settingsdir)

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

    async def test_loadModule(self):
        """Test adding and removal of module"""
        self.manager.addModule("PaGS.modules.paramModule")

        # is the module loaded?
        # (noting that internalPrinter is already loaded)
        assert len(self.manager.multiModules) == 2
        assert "param" in self.manager.commands
        assert len(self.manager.commands["param"]) == 6

        await self.manager.removeModule("PaGS.modules.paramModule")

        # is the module unloaded?
        assert len(self.manager.multiModules) == 1
        assert "param" not in self.manager.commands

    async def test_cmd_download(self):
        """Test the "download" command"""
        self.manager.addModule("PaGS.modules.paramModule")

        # execute a command
        self.manager.onModuleCommandCallback("VehA", "param download")

        # assert
        await asyncio.sleep(0.001)
        assert self.txVehPackets['VehA'] is not None

    async def test_cmd_status(self):
        """Test the "status" command"""
        self.manager.addModule("PaGS.modules.paramModule")

        # execute a command
        self.manager.onModuleCommandCallback("VehA", "param status")

        # assert printed
        assert self.getOutText("VehA", 1) == "Params not downloaded"

        # now we have some params downloaded
        self.VehA.paramstatus = [15, 20, [1, 2, 4, 6, 13]]

        # execute a command
        self.manager.onModuleCommandCallback("VehA", "param status")

        # assert
        assert self.getOutText("VehA", 3) == "Downloaded 5 of 20 params"

        # now all params downloaded
        self.VehA.paramstatus = True

        # execute a command
        self.manager.onModuleCommandCallback("VehA", "param status")

        # assert
        assert self.getOutText("VehA", 5) == "Got all (0) params"

    async def test_cmd_show(self):
        """Test the "show" command"""
        self.manager.addModule("PaGS.modules.paramModule")

        # test with no params
        self.manager.onModuleCommandCallback("VehA", "param show *")

        # assert
        assert self.getOutText("VehA", 1) == "Params not downloaded"

        # now all params downloaded
        self.VehA.paramstatus = True
        self.VehA.params = {"RC1_MIN": 1000, "RC2_MAX": 2000}

        # get one param
        self.manager.onModuleCommandCallback("VehA", "param show RC1_MIN")
        assert self.getOutText("VehA", 3) == "RC1_MIN          1000"

        # get several params
        self.manager.onModuleCommandCallback("VehA", "param show RC*")
        allstr = self.getOutText("VehA", 5) + ", " + self.getOutText("VehA", 6)
        assert "RC1_MIN          1000" in allstr
        assert "RC2_MAX          2000" in allstr

        # get not existing param
        self.manager.onModuleCommandCallback("VehA", "param show RC5_MAX")
        assert self.getOutText("VehA", 8) == "No param RC5_MAX"

        # get no param
        self.manager.onModuleCommandCallback("VehA", "param show")
        assert "Traceback" in self.getOutText("VehA", 10)

    async def test_cmd_set(self):
        """Test the "set" command"""
        self.manager.addModule("PaGS.modules.paramModule")

        # test with no params
        self.manager.onModuleCommandCallback("VehA", "param set RC1_MIN 1102")

        # assert
        assert self.getOutText("VehA", 1) == "Params not downloaded"

        # now all params downloaded
        self.VehA.paramstatus = True
        self.VehA.params = {"RC1_MIN": 1000, "RC2_MAX": 2000}
        self.VehA.params_type = {
            "RC1_MIN": self.mod.MAV_PARAM_TYPE_UINT16,
            "RC2_MAX": self.mod.MAV_PARAM_TYPE_UINT16}

        # test with single param
        self.manager.onModuleCommandCallback("VehA", "param set RC1_MIN 1102")
        # assert
        await asyncio.sleep(0.1)
        assert self.txVehPackets['VehA'] is not None

        # test with not existing param
        self.manager.onModuleCommandCallback("VehA", "param set RC1_MAX 1102")
        # assert
        assert self.getOutText("VehA", 4) == "No param with that name"

        # test with invalid val
        self.manager.onModuleCommandCallback("VehA", "param set RC1_MIN fgda")
        # assert
        assert self.getOutText("VehA", 6) == "Invalid param value"

        # test with no val
        self.manager.onModuleCommandCallback("VehA", "param set RC1_MIN")
        # assert
        assert "Traceback" in self.getOutText("VehA", 8)

    def test_cmd_save(self):
        """Test the save param command"""
        self.manager.addModule("PaGS.modules.paramModule")

        # test with no params
        self.manager.onModuleCommandCallback("VehA", "param save temp.parm")

        # assert
        assert self.getOutText("VehA", 1) == "Params not downloaded"

        # now all params downloaded
        self.VehA.paramstatus = True
        self.VehA.params = {"RC1_MIN": 1000, "RC2_MAX": 2000}
        self.VehA.params_type = {
            "RC1_MIN": self.mod.MAV_PARAM_TYPE_UINT16,
            "RC2_MAX": self.mod.MAV_PARAM_TYPE_UINT16}

        # test with params
        self.manager.onModuleCommandCallback("VehA", "param save temp.parm")
        # assert
        assert self.getOutText("VehA", 3) == "2 params saved to temp.parm"
        assert os.path.isfile("temp.parm")
        with open('temp.parm', 'r') as myfile:
            data = myfile.read()
        assert "RC1_MIN          1000\n" in data
        assert "RC2_MAX          2000\n" in data

        # test with space in filename
        self.manager.onModuleCommandCallback(
            "VehA", "param save \"temp 1.parm\"")
        # assert
        assert self.getOutText("VehA", 5) == "2 params saved to temp 1.parm"
        assert os.path.isfile("temp 1.parm")
        with open('temp 1.parm', 'r') as myfile:
            data = myfile.read()
        assert "RC1_MIN          1000\n" in data
        assert "RC2_MAX          2000\n" in data

        # and clean up files
        os.remove("temp.parm")
        os.remove("temp 1.parm")

    async def test_cmd_load(self):
        """Test the load param command"""
        self.manager.addModule("PaGS.modules.paramModule")

        # create the param files - good, param name bad, param value bad,
        # corrupt
        with open('tempload.parm', 'w') as myfile:
            myfile.write("RC1_MIN          1100\nRC2_MAX          2100\n")
        with open('temploadbad1.parm', 'w') as myfile:
            myfile.write("RC1_MID          1100\nRC2_MAX          2100\n")
        with open('temploadbad2.parm', 'w') as myfile:
            myfile.write("RC1_MIN          1100\nRC2_MAX          dsf\n")
        with open('temploadbad3.parm', 'w') as myfile:
            myfile.write("w309836nb32n98n72\nw983n5c032 948")

        # test with no params
        self.manager.onModuleCommandCallback(
            "VehA", "param load tempload.parm")

        # assert
        assert self.getOutText("VehA", 1) == "Params not downloaded"

        # now all params downloaded
        self.VehA.paramstatus = True
        self.VehA.params = {"RC1_MIN": 1000, "RC2_MAX": 2000}
        self.VehA.params_type = {
            "RC1_MIN": self.mod.MAV_PARAM_TYPE_UINT16,
            "RC2_MAX": self.mod.MAV_PARAM_TYPE_UINT16}

        # test the normal good file
        self.manager.onModuleCommandCallback(
            "VehA", "param load tempload.parm")

        # and assert
        assert self.getOutText(
            "VehA", 3) == "2 params loaded from tempload.parm"
        await asyncio.sleep(0.01)
        assert self.txVehPackets['VehA'] is not None

        # bad file 1 - wrong param name
        self.manager.onModuleCommandCallback(
            "VehA", "param load temploadbad1.parm")

        # and assert
        assert self.getOutText("VehA", 5) == "Invalid param: RC1_MID"
        assert self.getOutText(
            "VehA", 6) == "1 params loaded from temploadbad1.parm"

        # bad file 2 - wrong param value
        self.manager.onModuleCommandCallback(
            "VehA", "param load temploadbad2.parm")

        # and assert
        assert self.getOutText("VehA", 8) == "Invalid param value: dsf"
        assert self.getOutText(
            "VehA", 9) == "1 params loaded from temploadbad2.parm"

        # bad file 3 - just plain corrupt
        self.manager.onModuleCommandCallback(
            "VehA", "param load temploadbad3.parm")

        # and assert
        assert self.getOutText(
            "VehA", 11) == "Param line not valid: w309836nb32n98n72"
        assert self.getOutText("VehA", 12) == "Invalid param: w983n5c032"
        assert self.getOutText(
            "VehA", 13) == "0 params loaded from temploadbad3.parm"

        # and clean up files
        os.remove("tempload.parm")
        os.remove("temploadbad1.parm")
        os.remove("temploadbad2.parm")
        os.remove("temploadbad3.parm")

    def test_guiStart(self):
        """Simple test of the GUI startup"""

        # need to reset for handling gui
        self.manager = moduleManager.moduleManager(self.loop, self.settingsdir, True)
        self.manager.onVehListAttach(self.getVehListCallback)
        self.manager.onVehGetAttach(self.getVehicleCallback)
        self.manager.onPktTxAttach(self.txcallback)

        self.manager.addModule("PaGS.modules.internalPrinterModule")

        self.manager.addModule("PaGS.modules.paramModule")

        # TODO: some GUI tests?

    def getOutText(self, Veh: str, line: int):
        """Helper function for getting output text from internalPrinterModule"""
        return self.manager.multiModules['PaGS.modules.internalPrinterModule'].printedout[Veh][line]

    def test_incoming(self):
        """Test incoming packets"""
        pass


if __name__ == '__main__':
    asynctest.main()
