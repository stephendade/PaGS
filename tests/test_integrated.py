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
Integrated tests of the link-vehicle-module triangle.

Tests include:
adding and removing vehicles
adding extra links to a vehicle
adding and removing modules

'''
import asyncio
import asynctest

from PaGS.managers.connectionManager import ConnectionManager
from PaGS.managers.vehicleManager import VehicleManager
from PaGS.managers.moduleManager import moduleManager

from PaGS.connection.tcplink import TCPConnection

from PaGS.mavlink.pymavutil import getpymavlinkpackage


class IntegratedTest(asynctest.TestCase):

    """
    Class to test the integrated link-vehicle-module connections
    """

    def setUp(self):
        """Set up some data that is reused in many tests"""
        self.dialect = 'ardupilotmega'
        self.version = 2.0
        self.port = 15000
        self.ip = "127.0.0.1"

        self.cname = 'tcpclient:127.0.0.1:15000'

        self.mod = getpymavlinkpackage(self.dialect, self.version)
        self.mav = self.mod.MAVLink(
            self, srcSystem=4, srcComponent=0, use_native=False)

        connmtrx = None
        allvehicles = None
        allModules = None

        self.cnum = 0

    def newpacketcallback(self, pkt, strconnection):
        """Callback when a link has a new packet"""
        if pkt.get_type is not 'BAD_DATA':
            if strconnection == self.cname:
                self.cnum += 1

    async def tearDown(self):
        """Called at the end of each test"""
        if self.allvehicles:
            for veh in self.allvehicles.get_vehiclelist():
                await self.allvehicles.remove_vehicle(veh)
        if self.connmtrx:
            await self.connmtrx.stoploop()

        #for task in asyncio.Task.all_tasks():
        #    task.cancel()

    async def doEventLinkages(self):
        """Create the event linkages. Assumes
        that connmtrx, allvehicles, allModules
        have been initialised
        """
        # event links from connmaxtrix -> vehicle manager
        self.connmtrx.onPacketAttach(self.allvehicles.onPacketRecieved)

        # event links from vehicle manager -> connmatrix
        self.allvehicles.onPacketBufTxAttach(self.connmtrx.outgoingPacket)
        await self.allvehicles.onLinkAddAttach(self.connmtrx.addVehicleLink)
        await self.allvehicles.onLinkRemoveAttach(self.connmtrx.removeLink)

        # event links from module manager -> vehicle manager
        self.allModules.onPktTxAttach(self.allvehicles.send_message)
        self.allModules.onVehListAttach(self.allvehicles.get_vehiclelist)
        self.allModules.onVehGetAttach(self.allvehicles.get_vehicle)

        # event links vehicle manager -> module manager
        self.allvehicles.onAddVehicleAttach(self.allModules.addVehicle)
        self.allvehicles.onRemoveVehicleAttach(self.allModules.removeVehicle)
        self.allvehicles.onPacketRxAttach(self.allModules.incomingPacket)

    async def test_startup(self):
        """ Test that we can cleanly startup and shutdown
        """
        # Start the connection maxtrix
        self.connmtrx = ConnectionManager(self.loop, self.dialect, self.version, 0, 0)

        # Dict of vehicles
        self.allvehicles = VehicleManager(self.loop)

        # Module manager
        self.allModules = moduleManager(self.loop, self.dialect, self.version, False)

        # and link them all together
        await self.doEventLinkages()



    async def test_singleConnection(self):
        """ Test that we can get a packet with a single
        vehicle with single connection
        """
        # Start the connection maxtrix
        self.connmtrx = ConnectionManager(self.loop, self.dialect, self.version, 0, 0)

        # Dict of vehicles
        self.allvehicles = VehicleManager(self.loop)

        # Module manager
        self.allModules = moduleManager(self.loop, self.dialect, self.version, False)

        # and link them all together
        await self.doEventLinkages()

        #add a link
        await self.allvehicles.add_vehicle("VehA", 255, 0, 4, 0,
                                    self.dialect, self.version, 'tcpserver:127.0.0.1:15000')

        # Start a remote connection (TCP)
        self.remoteClient = TCPConnection(rxcallback=self.newpacketcallback,
                               dialect=self.dialect, mavversion=self.version,
                               srcsystem=0, srccomp=0,
                               server=False, name=self.cname)

        await asyncio.sleep(0.3)

        await self.loop.create_connection(lambda: self.remoteClient, self.ip, self.port)

        # wait for 0.02 sec
        await asyncio.sleep(0.02)

        # send a heartbeat packet
        pkt = self.mod.MAVLink_heartbeat_message(
            5, 4, 0, 0, 0, int(self.version))
        self.remoteClient.send_data(pkt.pack(self.mav, force_mavlink1=False))

        await asyncio.sleep(0.02)

        self.remoteClient.close()

        # assert the vehicle recieved the packet
        assert len(self.allvehicles.get_vehicle("VehA").latestPacketDict) == 1
        assert self.allvehicles.get_vehicle("VehA").latestPacketDict[0] == pkt

if __name__ == '__main__':
    asynctest.main()
