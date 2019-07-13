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

'''Connectionmatrix tests

Can add and remove links to vehicles DONE
Can add and remove vehicles (with associated link/sysid) DONE
Incoming packets distributed to correct vehicle DONE
Outgoing packet distributed to correct vehicle DONE
If link is lost/crashed, try to keep connecting DONE
Can get list of links per vehicle, with link status
Duplicate incoming packets are discarded DONE
Check that vehicle name, sysid are unique
Check that links are unique

For distribution, combos are:
-Single link, shared link, multilink
-VehA: LinkA,LinkB, VehB: LinkB, VehC: LinkC

For each, ensure packets are routed, noting that duplicate
packets will be discarded

'''

import asyncio
import asynctest

from PaGS.connection.tcplink import TCPConnection
from PaGS.connection.udplink import UDPConnection
from PaGS.mavlink.pymavutil import getpymavlinkpackage
from PaGS.managers.connectionManager import ConnectionManager
from PaGS.vehicle.vehicle import Vehicle


class ConnectionMatrixTest(asynctest.TestCase):

    """
    Class to test The connection matrix
    """

    def setUp(self):
        """Set up some data that is reused in many tests"""
        self.dialect = 'ardupilotmega'
        self.version = 2.0
        self.ip = "127.0.0.1"

        # The links
        self.linkA = 'tcpclient:127.0.0.1:15001'
        self.linkB = 'tcpserver:127.0.0.1:15020'
        self.linkC = 'udpclient:127.0.0.1:15002'
        self.linkD = 'udpserver:127.0.0.1:15021'

        # The vehicles. Note the vehicles A and C have the same sysid
        # Source s/c then target s/c
        self.VehA = Vehicle(self.loop, "VehA", 255, 0, 4,
                            0, self.dialect, self.version)
        self.VehB = Vehicle(self.loop, "VehB", 254, 0, 3,
                            0, self.dialect, self.version)
        self.VehC = Vehicle(self.loop, "VehC", 255, 0, 4,
                            0, self.dialect, self.version)

        # Dict of data rx'd by each link
        self.rxdata = {}

        # Dict of data rx'd by each vehicle
        self.vehpkts = {}

        self.mod = getpymavlinkpackage(self.dialect, self.version)
        # From the vehicle
        self.mavUAS = self.mod.MAVLink(
            self, srcSystem=4, srcComponent=0, use_native=False)
        self.mavoneUAS = self.mod.MAVLink(
            self, srcSystem=3, srcComponent=0, use_native=False)
        self.mavGCS = self.mod.MAVLink(
            self, srcSystem=255, srcComponent=0, use_native=False)
        self.mavoneGCS = self.mod.MAVLink(
            self, srcSystem=254, srcComponent=0, use_native=False)

    async def tearDown(self):
        """Called at the end of each test"""
        await self.VehA.stopheartbeat()
        await self.VehB.stopheartbeat()
        await self.VehC.stopheartbeat()
        await self.VehA.stoprxtimeout()
        await self.VehB.stoprxtimeout()
        await self.VehC.stoprxtimeout()

    def newpacketcallbackVeh(self, vehname, pkt, strconnection):
        """Callback when a vehicle has a new packet"""
        try:
            self.vehpkts[vehname].append(pkt)
        except KeyError:
            self.vehpkts[vehname] = [pkt]

    def newpacketcallbackLnk(self, pkt, strconnection):
        """Callback when a test link has a new packet"""
        try:
            self.rxdata[strconnection].append(pkt)
        except KeyError:
            self.rxdata[strconnection] = [pkt]

    async def test_matrixstartup(self):
        """Test a simple startup of the matrix"""
        matrix = ConnectionManager(self.loop, self.dialect, self.version, 0, 0)

        await matrix.stoploop()

        assert matrix is not None

    async def test_matrixaddremove(self):
        """Test adding and removing vehicles from the matrix"""
        matrix = ConnectionManager(self.loop, self.dialect, self.version, 0, 0)
        matrix.onPacketAttach(self.newpacketcallbackVeh)

        await matrix.addVehicleLink(self.VehA.name, self.VehA.target_system, self.linkB)
        await matrix.addVehicleLink(self.VehB.name, self.VehB.target_system, self.linkB)
        await matrix.addVehicleLink(self.VehC.name, self.VehC.target_system, self.linkD)

        # now wait for a bit - 0.02 sec
        await asyncio.sleep(0.02)

        assert len(matrix.getAllVeh()) == 3
        assert len(matrix.linkdict) == 2

        # remove a link - it will remove the associated veh C too
        await matrix.removeLink(self.linkD)

        # now wait for a bit - 0.02 sec
        await asyncio.sleep(0.02)

        assert len(matrix.getAllVeh()) == 2
        assert len(matrix.linkdict) == 1

        # remove a vehicle
        await matrix.removeVehicle(self.VehA.name)

        # now wait for a bit - 0.02 sec
        await asyncio.sleep(0.02)

        await matrix.stoploop()

        # assert. It should be VehA and linkB left
        assert len(matrix.getAllVeh()) == 1
        assert len(matrix.linkdict) == 1

    async def test_linkretry_tcp(self):
        """For each of the TCP link types, test that they
        keep re-trying to connect, by only adding in the
        other side of the link 0.5 sec after startup"""
        matrix = ConnectionManager(
            self.loop, self.dialect, self.version, 0, 0, 0.05)
        matrix.onPacketAttach(self.newpacketcallbackVeh)

        await matrix.addVehicleLink(self.VehA.name, self.VehA.target_system, self.linkA)
        await matrix.addVehicleLink(self.VehB.name, self.VehB.target_system, self.linkB)

        # now wait for a bit
        await asyncio.sleep(0.10)

        # now connect the other sides
        tcpserver = TCPConnection(rxcallback=self.newpacketcallbackLnk,
                                  dialect=self.dialect, mavversion=self.version,
                                  srcsystem=0, srccomp=0,
                                  server=True, name='tcpserver:127.0.0.1:15001')
        tcpclient = TCPConnection(rxcallback=self.newpacketcallbackLnk,
                                  dialect=self.dialect, mavversion=self.version,
                                  srcsystem=0, srccomp=0,
                                  server=False, name='tcpclient:127.0.0.1:15020')
        await self.loop.create_server(lambda: tcpserver, self.ip, 15001)
        await self.loop.create_connection(lambda: tcpclient, self.ip, 15020)

        # send packets on each link and wait
        await asyncio.sleep(0.20)

        pkt = self.mod.MAVLink_heartbeat_message(
            5, 4, 0, 0, 0, int(self.version))
        pktbytes = pkt.pack(self.mavUAS, force_mavlink1=False)
        pktbytesone = pkt.pack(self.mavoneUAS, force_mavlink1=False)
        tcpserver.send_data(pktbytes)
        tcpclient.send_data(pktbytesone)

        await asyncio.sleep(0.20)

        await matrix.stoploop()

        tcpserver.close()
        tcpclient.close()

        # assert the links are all still there
        assert len(matrix.getAllVeh()) == 2
        assert len(matrix.linkdict) == 2

        # assert packets were recived on both links (vehicles) in the matrix
        assert self.vehpkts[self.VehA.name][0].get_msgbuf() == pktbytes
        assert self.vehpkts[self.VehB.name][0].get_msgbuf() == pktbytesone

    async def test_linkretry_udp(self):
        """For each of the UDP link types, test that they
        keep re-trying to connect, by only adding in the
        other side of the link 0.5 sec after startup"""
        matrix = ConnectionManager(
            self.loop, self.dialect, self.version, 0, 0, 0.05)
        matrix.onPacketAttach(self.newpacketcallbackVeh)

        self.VehA.onPacketTxAttach(matrix.outgoingPacket)
        self.VehB.onPacketTxAttach(matrix.outgoingPacket)

        await matrix.addVehicleLink(self.VehA.name, self.VehA.target_system, self.linkC)
        await matrix.addVehicleLink(self.VehB.name, self.VehB.target_system, self.linkD)

        # now wait for a bit - 0.02 sec
        await asyncio.sleep(0.02)

        # now connect the other sides
        udpserver = UDPConnection(rxcallback=self.newpacketcallbackLnk,
                                  dialect=self.dialect, mavversion=self.version,
                                  srcsystem=0, srccomp=0,
                                  server=True, name='udpserver:127.0.0.1:15002')
        udpclient = UDPConnection(rxcallback=self.newpacketcallbackLnk,
                                  dialect=self.dialect, mavversion=self.version,
                                  srcsystem=0, srccomp=0,
                                  server=False, name='udpclient:127.0.0.1:15021')
        await self.loop.create_datagram_endpoint(lambda: udpserver,
                                                 local_addr=(self.ip, 15002))
        await self.loop.create_datagram_endpoint(lambda: udpclient,
                                                 remote_addr=(self.ip, 15021))

        # send packets on each link and wait 0.02 sec
        await asyncio.sleep(0.02)

        pkt = self.mod.MAVLink_heartbeat_message(
            5, 4, 0, 0, 0, int(self.version))
        pktbytes = pkt.pack(self.mavUAS, force_mavlink1=False)
        pktbytesone = pkt.pack(self.mavoneUAS, force_mavlink1=False)

        # need to send a packet from client to server to init the link
        self.VehA.sendPacket(self.VehA.mod.MAVLINK_MSG_ID_HEARTBEAT,
                             type=self.VehA.mod.MAV_TYPE_GCS,
                             autopilot=self.VehA.mod.MAV_AUTOPILOT_INVALID,
                             base_mode=0,
                             custom_mode=0,
                             system_status=0,
                             mavlink_version=int(self.VehA.mavversion))

        await asyncio.sleep(0.02)

        udpserver.send_data(pktbytes)
        udpclient.send_data(pktbytesone)

        await asyncio.sleep(0.02)

        await matrix.stoploop()

        udpserver.close()
        udpclient.close()

        # assert the links are all still there
        assert len(matrix.getAllVeh()) == 2
        assert len(matrix.linkdict) == 2

        # assert packets were recived on both links (vehicles) in the matrix
        assert len(self.vehpkts) == 2
        assert self.vehpkts[self.VehA.name][0].get_msgbuf() == pktbytes
        assert self.vehpkts[self.VehB.name][0].get_msgbuf() == pktbytesone

    async def test_incomingdistribution(self):
        """Test incoming packets (from vehicle) are distributed
        correctly"""
        # -VehA: LinkA,LinkB, VehB: LinkB, VehC: LinkC
        matrix = ConnectionManager(
            self.loop, self.dialect, self.version, 0, 0, 0.05)
        matrix.onPacketAttach(self.newpacketcallbackVeh)

        await matrix.addVehicleLink(self.VehA.name, self.VehA.target_system, self.linkA)
        await matrix.addVehicleLink(self.VehA.name, self.VehA.target_system, self.linkB)
        await matrix.addVehicleLink(self.VehB.name, self.VehB.target_system, self.linkB)
        await matrix.addVehicleLink(self.VehC.name, self.VehC.target_system, self.linkD)

        # now wait for a bit
        await asyncio.sleep(0.10)

        # now connect the other sides
        tcpserver = TCPConnection(rxcallback=self.newpacketcallbackLnk,
                                  dialect=self.dialect, mavversion=self.version,
                                  srcsystem=0, srccomp=0,
                                  server=True, name='tcpserver:127.0.0.1:15001')
        tcpclient = TCPConnection(rxcallback=self.newpacketcallbackLnk,
                                  dialect=self.dialect, mavversion=self.version,
                                  srcsystem=0, srccomp=0,
                                  server=False, name='tcpclient:127.0.0.1:15020')
        udpclient = UDPConnection(rxcallback=self.newpacketcallbackLnk,
                                  dialect=self.dialect, mavversion=self.version,
                                  srcsystem=0, srccomp=0,
                                  server=False, name='udpclient:127.0.0.1:15021')
        await self.loop.create_server(lambda: tcpserver, self.ip, 15001)
        await self.loop.create_connection(lambda: tcpclient, self.ip, 15020)
        await self.loop.create_datagram_endpoint(lambda: udpclient,
                                                 remote_addr=(self.ip, 15021))

        # send packets on each link and wait
        await asyncio.sleep(0.10)

        pkt = self.mod.MAVLink_heartbeat_message(
            5, 4, 0, 0, 0, int(self.version))
        pktbytes = pkt.pack(self.mavUAS, force_mavlink1=False)
        pktbytesone = pkt.pack(self.mavoneUAS, force_mavlink1=False)

        # send packet to VehA on LinkA
        tcpserver.send_data(pktbytes)
        await asyncio.sleep(0.10)

        # send new (updated) packet to VehA on LinkB
        pktupdate = self.mod.MAVLink_heartbeat_message(
            5, 3, 0, 0, 0, int(self.version))
        pktbytesupdate = pktupdate.pack(self.mavUAS, force_mavlink1=False)
        tcpclient.send_data(pktbytesupdate)

        # need a small sleep here otherwise the linkB gets confused
        await asyncio.sleep(0.10)

        # send packet to VehB on linkB
        tcpclient.send_data(pktbytesone)
        await asyncio.sleep(0.10)

        # send packet to VehC on LinkC
        udpclient.send_data(pktbytes)

        # wait for packets to send
        await asyncio.sleep(0.10)

        # and close everything
        await matrix.stoploop()

        tcpserver.close()
        tcpclient.close()
        udpclient.close()

        # assert the links are all still there
        assert len(matrix.getAllVeh()) == 3
        assert len(matrix.linkdict) == 3

        # assert packets were recived
        assert self.vehpkts[self.VehA.name][0].get_msgbuf() == pktbytes
        assert self.vehpkts[self.VehA.name][1].get_msgbuf() == pktbytesupdate
        assert self.vehpkts[self.VehB.name][0].get_msgbuf() == pktbytesone
        assert self.vehpkts[self.VehC.name][0].get_msgbuf() == pktbytes

    async def test_outgoingdistribution(self):
        """Test outgoing packets (from gcs) are distributed
        correctly"""
        # -VehA: LinkA,LinkB, VehB: LinkB, VehC: LinkC
        await self.VehA.setHearbeatRate(0)
        await self.VehB.setHearbeatRate(0)
        await self.VehC.setHearbeatRate(0)

        matrix = ConnectionManager(
            self.loop, self.dialect, self.version, 0, 0, 0.05)
        matrix.onPacketAttach(self.newpacketcallbackVeh)

        self.VehA.onPacketTxAttach(matrix.outgoingPacket)
        self.VehB.onPacketTxAttach(matrix.outgoingPacket)
        self.VehC.onPacketTxAttach(matrix.outgoingPacket)

        await matrix.addVehicleLink(self.VehA.name, self.VehA.target_system, self.linkA)
        await matrix.addVehicleLink(self.VehA.name, self.VehA.target_system, self.linkB)
        await matrix.addVehicleLink(self.VehB.name, self.VehB.target_system, self.linkB)
        await matrix.addVehicleLink(self.VehC.name, self.VehC.target_system, self.linkC)

        # now wait for a bit
        await asyncio.sleep(0.15)

        # now connect the other sides
        tcpserver = TCPConnection(rxcallback=self.newpacketcallbackLnk,
                                  dialect=self.dialect, mavversion=self.version,
                                  srcsystem=0, srccomp=0,
                                  server=True, name='tcpserver:127.0.0.1:15001')
        tcpclient = TCPConnection(rxcallback=self.newpacketcallbackLnk,
                                  dialect=self.dialect, mavversion=self.version,
                                  srcsystem=0, srccomp=0,
                                  server=False, name='tcpclient:127.0.0.1:15020')
        udpserver = UDPConnection(rxcallback=self.newpacketcallbackLnk,
                                  dialect=self.dialect, mavversion=self.version,
                                  srcsystem=0, srccomp=0,
                                  server=True, name='udpserver:127.0.0.1:15002')
        await self.loop.create_server(lambda: tcpserver, self.ip, 15001)
        await self.loop.create_connection(lambda: tcpclient, self.ip, 15020)
        await self.loop.create_datagram_endpoint(lambda: udpserver,
                                                 local_addr=(self.ip, 15002))

        # send packets on each link and wait
        await asyncio.sleep(0.15)

        # send packet from the GCS of VehA, VehB and VehC
        pktbytesA = self.VehA.sendPacket(self.mod.MAVLINK_MSG_ID_HEARTBEAT,
                                         type=self.mod.MAV_TYPE_GCS,
                                         autopilot=self.mod.MAV_AUTOPILOT_INVALID,
                                         base_mode=0,
                                         custom_mode=0,
                                         system_status=0,
                                         mavlink_version=int(self.VehA.mavversion))
        await asyncio.sleep(0.10)
        pktbytesB = self.VehB.sendPacket(self.mod.MAVLINK_MSG_ID_HEARTBEAT,
                                         type=self.mod.MAV_TYPE_GCS,
                                         autopilot=self.mod.MAV_AUTOPILOT_INVALID,
                                         base_mode=0,
                                         custom_mode=0,
                                         system_status=0,
                                         mavlink_version=int(self.VehB.mavversion))
        await asyncio.sleep(0.10)
        pktbytesC = self.VehC.sendPacket(self.mod.MAVLINK_MSG_ID_HEARTBEAT,
                                         type=self.mod.MAV_TYPE_GCS,
                                         autopilot=self.mod.MAV_AUTOPILOT_INVALID,
                                         base_mode=0,
                                         custom_mode=0,
                                         system_status=0,
                                         mavlink_version=int(self.VehC.mavversion))

        # wait for packets to send
        await asyncio.sleep(0.15)

        # and close everything
        await matrix.stoploop()

        tcpserver.close()
        tcpclient.close()
        udpserver.close()

        # assert the links are all still there
        assert len(matrix.getAllVeh()) == 3
        assert len(matrix.linkdict) == 3

        # assert packets were recived on the endpoints
        assert self.rxdata['tcpserver:127.0.0.1:15001'][0].get_msgbuf(
        ) == pktbytesA
        assert self.rxdata['tcpclient:127.0.0.1:15020'][0].get_msgbuf(
        ) == pktbytesC
        assert self.rxdata['tcpclient:127.0.0.1:15020'][1].get_msgbuf(
        ) == pktbytesB
        assert self.rxdata['udpserver:127.0.0.1:15002'][0].get_msgbuf(
        ) == pktbytesC


if __name__ == '__main__':
    asynctest.main()
