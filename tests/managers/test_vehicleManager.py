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

'''Vehicle manager tests

Can add and remove vehicles DONE
Callbacks to connectionManager for add/remove vehicles
Callbacks to connectionManager for rx/tx packets
Can't add vehicle with same name

'''
import asynctest
import asyncio

from PaGS.managers import vehicleManager
from PaGS.mavlink.pymavutil import getpymavlinkpackage


class VehicleManagerTest(asynctest.TestCase):

    """
    Class to test vehicleManager
    """

    def setUp(self):
        """Set up some data that is reused in many tests"""

        self.manager = None

        self.dialect = 'ardupilotmega'
        self.version = 2.0
        self.mod = getpymavlinkpackage(self.dialect, self.version)
        self.mavUAS = self.mod.MAVLink(
            self, srcSystem=4, srcComponent=0, use_native=False)

        self.callbacks = {}

    async def tearDown(self):
        """Close down the test - remove all vehicles"""
        if self.manager:
            for veh in self.manager.get_vehiclelist():
                await self.manager.remove_vehicle(veh)

    async def linkaddcallback(self, vehname, target_system, strconnection):
        """Callback for link add"""
        self.callbacks['linkadd'] = (vehname, target_system, strconnection)

    async def linkremovecallback(self, vehname):
        """Callback for link remove"""
        self.callbacks['linkremove'] = (vehname)

    def vehicleaddcallback(self, vehname):
        """Callback for module vehicle add"""
        self.callbacks['vehicleadd'] = (vehname)

    def vehicleremovecallback(self, vehname):
        """Callback for module vehicle remove"""
        self.callbacks['vehicleremove'] = (vehname)

    def pktbuffertxcallback(self, buf, vehname):
        """Callback for sending a packet buffer"""
        self.callbacks['pktbuffertx'] = (vehname, buf)

    def test_manager(self):
        """Check initialisation"""
        self.manager = vehicleManager.VehicleManager(self.loop)

        assert len(self.manager.veh_list) == 0

    async def test_addremovevehicle(self):
        """Add and remove vehicles, plus callbacks"""
        self.manager = vehicleManager.VehicleManager(self.loop)
        # Add callbacks
        await self.manager.onLinkAddAttach(self.linkaddcallback)
        await self.manager.onLinkRemoveAttach(self.linkremovecallback)
        self.manager.onAddVehicleAttach(self.vehicleaddcallback)
        self.manager.onRemoveVehicleAttach(self.vehicleremovecallback)

        await self.manager.add_vehicle(
            "VehA", 255, 0, 4, 0, self.dialect, self.version, 'tcpclient:127.0.0.1:15001')
        assert self.callbacks['linkadd'] == (
            "VehA", 4, 'tcpclient:127.0.0.1:15001')
        assert self.callbacks['vehicleadd'] == ("VehA")

        await self.manager.add_vehicle(
            "VehB", 254, 0, 3, 0, self.dialect, self.version, 'tcpserver:127.0.0.1:15020')
        assert self.callbacks['linkadd'] == (
            "VehB", 3, 'tcpserver:127.0.0.1:15020')
        assert self.callbacks['vehicleadd'] == ("VehB")

        assert len(self.manager.get_vehiclelist()) == 2

        await self.manager.remove_vehicle("VehB")

        assert self.callbacks['linkremove'] == ("VehB")
        assert self.callbacks['vehicleremove'] == ("VehB")
        assert self.manager.get_vehiclelist() == ["VehA"]

        await self.manager.remove_vehicle("VehA")

        assert len(self.manager.get_vehiclelist()) == 0
        assert self.callbacks['linkremove'] == ("VehA")
        assert self.callbacks['vehicleremove'] == ("VehA")

    async def test_addvehiclemultilink(self):
        """Add multiple links for a vehicle, plus callbacks"""
        self.manager = vehicleManager.VehicleManager(self.loop)
        # Add callbacks
        await self.manager.onLinkAddAttach(self.linkaddcallback)
        self.manager.onAddVehicleAttach(self.vehicleaddcallback)

        await self.manager.add_vehicle(
            "VehA", 255, 0, 4, 0, self.dialect, self.version, 'tcpclient:127.0.0.1:15001')
        await asyncio.sleep(0.5)
        assert self.callbacks['linkadd'] == (
            "VehA", 4, 'tcpclient:127.0.0.1:15001')
        assert self.callbacks['vehicleadd'] == ("VehA")
        self.callbacks = {}

        await self.manager.add_extraLink("VehA", 'tcpserver:127.0.0.1:15021')
        assert self.callbacks['linkadd'] == (
            "VehA", 4, 'tcpserver:127.0.0.1:15021')
        assert 'vehicleadd' not in self.callbacks

    async def test_removeerror(self):
        """try removing a vehicle that does not exist"""
        self.manager = vehicleManager.VehicleManager(self.loop)
        # Add callbacks
        await self.manager.onLinkAddAttach(self.linkaddcallback)
        self.manager.onAddVehicleAttach(self.vehicleaddcallback)
        self.manager.onRemoveVehicleAttach(self.vehicleremovecallback)

        await self.manager.add_vehicle(
            "VehA", 255, 0, 4, 0, self.dialect, self.version, 'tcpclient:127.0.0.1:15001')
        self.callbacks = {}

        with self.assertRaises(Exception) as context:
            await self.manager.remove_vehicle("VehX")

        assert 'No vehicle with that name' in str(context.exception)
        assert self.callbacks == {}

    async def test_addlinkerror(self):
        """add a link to a vehicle that does not exist"""
        self.manager = vehicleManager.VehicleManager(self.loop)
        # Add callbacks
        await self.manager.onLinkAddAttach(self.linkaddcallback)
        self.manager.onAddVehicleAttach(self.vehicleaddcallback)

        await self.manager.add_vehicle(
            "VehA", 255, 0, 4, 0, self.dialect, self.version, 'tcpclient:127.0.0.1:15001')
        self.callbacks = {}

        with self.assertRaises(Exception) as context:
            await self.manager.add_extraLink("VehX", 'tcpclient:127.0.0.1:15021')

        assert 'No vehicle with that name' in str(context.exception)
        assert self.callbacks == {}

    async def test_packetRx(self):
        """Packet passing from connection manager -> vehiclemanager"""
        self.manager = vehicleManager.VehicleManager(self.loop)
        await self.manager.add_vehicle(
            "VehA", 255, 0, 4, 0, self.dialect, self.version, 'tcpclient:127.0.0.1:15001')
        await self.manager.add_vehicle(
            "VehB", 255, 0, 5, 0, self.dialect, self.version, 'tcpclient:127.0.0.1:15021')

        pkt = self.mod.MAVLink_heartbeat_message(
            5, 4, 0, 0, 0, int(self.version))
        self.manager.onPacketRecieved("VehA", pkt, 'tcpclient:127.0.0.1:15001')

        assert len(self.manager.get_vehicle("VehA").latestPacketDict) == 1
        assert self.manager.get_vehicle("VehA").latestPacketDict[0] == pkt

        assert len(self.manager.get_vehicle("VehB").latestPacketDict) == 0

    async def test_packetTx(self):
        """Packet passing from vehicle to connectionManager"""
        self.manager = vehicleManager.VehicleManager(self.loop)
        self.manager.onPacketBufTxAttach(self.pktbuffertxcallback)
        await self.manager.add_vehicle(
            "VehA", 255, 0, 4, 0, self.dialect, self.version, 'tcpclient:127.0.0.1:15001')
        await self.manager.add_vehicle(
            "VehB", 255, 0, 5, 0, self.dialect, self.version, 'tcpclient:127.0.0.1:15021')

        # Send a packet from GCS to Veh
        self.manager.get_vehicle("VehA").sendPacket(self.mod.MAVLINK_MSG_ID_HEARTBEAT,
                                                    type=self.mod.MAV_TYPE_GCS,
                                                    autopilot=self.mod.MAV_AUTOPILOT_INVALID,
                                                    base_mode=0,
                                                    custom_mode=0,
                                                    system_status=0,
                                                    mavlink_version=int(self.version))

        assert self.callbacks['pktbuffertx'][0] == "VehA"
        assert self.callbacks['pktbuffertx'][1] is not None

    async def test_getVehicle(self):
        """Test getting a vehicle from the manager"""
        self.manager = vehicleManager.VehicleManager(self.loop)
        self.manager.onPacketBufTxAttach(self.pktbuffertxcallback)
        await self.manager.add_vehicle(
            "VehA", 255, 0, 4, 0, self.dialect, self.version, 'tcpclient:127.0.0.1:15001')
        await self.manager.add_vehicle(
            "VehB", 255, 0, 5, 0, self.dialect, self.version, 'tcpclient:127.0.0.1:15021')

        with self.assertRaises(Exception) as context:
            self.manager.get_vehicle("VehX")

        assert 'No vehicle with that name' in str(context.exception)
        assert self.manager.get_vehicle("VehA") is not None
        assert self.manager.get_vehicle("VehA").name == "VehA"


if __name__ == '__main__':
    asynctest.main()
