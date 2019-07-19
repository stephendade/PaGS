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

'''Module manager tests

Can add and remove modules
Can pass through vehicle add/del events
Can pass through vehicle Packet Rx/Tx

TODO:
add and remove vehicle

'''

import asynctest

from PaGS.managers import moduleManager
from PaGS.vehicle.vehicle import Vehicle
from PaGS.mavlink.pymavutil import getpymavlinkpackage


class ModuleManagerTest(asynctest.TestCase):

    """
    Class to test moduleManager
    Doesn't strictly need to be asynctest, but
    just keeping it consistent with the other tests
    for now
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

        self.txPackets = {}

    def tearDown(self):
        """Close down the test"""
        pass

    def txcallback(self, name, pkt, **kwargs):
        """Event callback to sending a packet on to vehiclemanager"""
        self.txPackets[name] = pkt

    def getVehListCallback(self):
        """Get list of vehicles"""
        return ["VehA"]

    def getVehListCallbackMany(self):
        """Get list of vehicles"""
        return ["VehA", "VehC"]

    def getVehicleCallback(self, vehname):
        """Get a particular vehicle"""
        if vehname == "VehA":
            return self.VehA
        else:
            raise ValueError('No vehicle with that name')

    def test_manager(self):
        """Check initialisation"""
        self.manager = moduleManager.moduleManager(self.loop, False)

        assert len(self.manager.multiModules) == 0

    def test_addremoveModule(self):
        """Test adding and removal of module"""
        self.manager = moduleManager.moduleManager(self.loop, False)
        self.manager.onVehListAttach(self.getVehListCallback)
        self.manager.onVehGetAttach(self.getVehicleCallback)

        self.manager.addModule("PaGS.modules.templateModule")

        assert len(self.manager.multiModules) == 1
        assert "template" in self.manager.commands
        assert len(self.manager.commands["template"]) == 2

        self.manager.removeModule("PaGS.modules.templateModule")

        assert len(self.manager.multiModules) == 0
        assert "template" not in self.manager.commands
        assert "PaGS.modules.templateModule" not in self.manager.printers

    def test_inoutPacket(self):
        """Test packets going in and out"""
        self.manager = moduleManager.moduleManager(self.loop, False)
        self.manager.onVehListAttach(self.getVehListCallback)
        self.manager.onVehGetAttach(self.getVehicleCallback)

        self.manager.addModule("PaGS.modules.templateModule")

        # And create the callback for packet tx/rx between vehicle and modules
        self.manager.onPktTxAttach(self.txcallback)

        # send an incoming packet. The template module will send it back out
        # again
        pkt = self.mod.MAVLink_heartbeat_message(
            5, 4, 0, 0, 0, int(self.version))
        self.manager.incomingPacket("VehA", pkt, "link1")

        assert self.manager.multiModules["PaGS.modules.templateModule"].pkts == 1
        print(self.txPackets)
        assert self.txPackets["VehA"] == 0  # the packet type

    def test_addRemoveVehicle(self):
        """Test adding and removing a vehicle"""
        self.manager = moduleManager.moduleManager(self.loop, False)
        self.manager.onVehListAttach(self.getVehListCallback)
        self.manager.onVehGetAttach(self.getVehicleCallback)

        self.manager.addModule("PaGS.modules.templateModule")

        # simulate some vehicles being added
        self.manager.addVehicle("VehB")
        self.manager.addVehicle("VehC")

        assert self.manager.multiModules['PaGS.modules.templateModule'].theVeh == [
            "VehA", "VehB", "VehC"]

        # and being removed
        self.manager.removeVehicle("VehB")

        assert self.manager.multiModules['PaGS.modules.templateModule'].theVeh == [
            "VehA", "VehC"]

    def test_addRemoveVehicleAfterModule(self):
        """Test adding and removing vehicles prior
        to module loading"""
        self.manager = moduleManager.moduleManager(self.loop, False)
        self.manager.onVehListAttach(self.getVehListCallbackMany)
        # self.manager.onVehGetAttach(self.getVehicleCallback)

        # simulate some vehicles being added
        self.manager.addVehicle("VehB")
        self.manager.addVehicle("VehC")
        # and being removed
        self.manager.removeVehicle("VehB")

        # load module
        self.manager.addModule("PaGS.modules.templateModule")

        assert self.manager.multiModules['PaGS.modules.templateModule'].theVeh == [
            "VehA", "VehC"]

    def test_printer(self):
        """Test the printer function (output)
        for the modules"""
        self.manager = moduleManager.moduleManager(self.loop, False)
        self.manager.onVehListAttach(self.getVehListCallbackMany)

        self.manager.addVehicle("VehB")
        self.manager.addVehicle("VehC")

        # load module
        self.manager.addModule("PaGS.modules.templateModule")

        # print some text
        self.manager.printVeh("VehB", "test text")
        self.manager.printVeh("VehC", "test text2")

        assert self.manager.multiModules['PaGS.modules.templateModule'].printedout["VehB"] == "test text"
        assert self.manager.multiModules['PaGS.modules.templateModule'].printedout["VehC"] == "test text2"

    def test_command(self):
        """Test the loading and execution of user commands
        in modules"""
        self.manager = moduleManager.moduleManager(self.loop, False)
        self.manager.onVehListAttach(self.getVehListCallbackMany)

        self.manager.addVehicle("VehB")
        self.manager.addVehicle("VehC")

        # load module
        self.manager.addModule("PaGS.modules.templateModule")

        # execute a command
        self.manager.onModuleCommandCallback(
            "VehB", "template do_stuff 1 \"the rest\"")

        # and invalid command
        self.manager.onModuleCommandCallback("VehB", "template do_nothing")

        # and assert
        assert self.manager.multiModules['PaGS.modules.templateModule'].printedout[
            "VehB"] == "Command not found: template do_nothing"
        assert self.manager.multiModules['PaGS.modules.templateModule'].calledStuff["VehB"] == "1,the rest"

    def test_moreCommand(self):
        """Test the stability of the command handler with all
        sorts of mangled uner input"""
        self.manager = moduleManager.moduleManager(self.loop, False)
        self.manager.onVehListAttach(self.getVehListCallbackMany)

        self.manager.addVehicle("VehB")
        self.manager.addVehicle("VehC")

        # load module
        self.manager.addModule("PaGS.modules.templateModule")

        # test the mangled inputs
        self.manager.onModuleCommandCallback("VehB", "")
        self.manager.onModuleCommandCallback("VehB", "template")
        self.manager.onModuleCommandCallback("VehB", "template do_stuff")
        self.manager.onModuleCommandCallback(
            "VehB", "template do_stuff 1 3 4 6 7")
        self.manager.onModuleCommandCallback("VehB", "template do_stuff \"4")
        self.manager.onModuleCommandCallback("VehB", "template:")
        self.manager.onModuleCommandCallback("VehB", "template do_stuff:")
        self.manager.onModuleCommandCallback("VehB", "template crash")

        # no need to assert, as we're just checking if any exceptions
        # were unhandled


if __name__ == '__main__':
    asynctest.main()
