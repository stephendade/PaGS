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

'''UDPLink tests

Can send and recieve data (client/server)

If a link fails (disconnected) the link should not crash.

'''

import asyncio
import asynctest

from PaGS.connection.udplink import UDPConnection
from PaGS.mavlink.pymavutil import getpymavlinkpackage


class UDPLinkTest(asynctest.TestCase):

    """
    Class to test UDPConnection
    """

    def setUp(self):
        """Set up some data that is reused in many tests"""
        self.dialect = 'ardupilotmega'
        self.version = 2.0
        self.ip = '127.0.0.1'
        self.port = 15000
        self.cname = 'udpclient:127.0.0.1:15000'
        self.sname = 'udpserver:127.0.0.1:15000'

        self.mod = getpymavlinkpackage(self.dialect, self.version)
        self.mav = self.mod.MAVLink(
            self, srcSystem=0, srcComponent=0, use_native=False)
        self.cnum = 0
        self.snum = 0

    def newpacketcallback(self, pkt, strconnection):
        """Callback when a link has a new packet"""
        if pkt.get_type() == 'HEARTBEAT':
            if strconnection == self.cname:
                self.cnum += 1
            elif strconnection == self.sname:
                self.snum += 1

    async def test_link_udp(self):
        """Test passing data between two udp connections"""
        client = UDPConnection(rxcallback=self.newpacketcallback,
                               dialect=self.dialect, mavversion=self.version,
                               srcsystem=0, srccomp=0, server=False, name=self.cname)

        server = UDPConnection(rxcallback=self.newpacketcallback,
                               dialect=self.dialect, mavversion=self.version,
                               srcsystem=0, srccomp=0, server=True, name=self.sname)

        await self.loop.create_datagram_endpoint(lambda: server,
                                                 local_addr=(self.ip, self.port))
        await self.loop.create_datagram_endpoint(lambda: client,
                                                 remote_addr=(self.ip, self.port))

        # send a mavlink packet each way:
        pkt = self.mod.MAVLink_heartbeat_message(
            5, 4, 0, 0, 0, int(self.version))
        client.send_data(pkt.pack(self.mav, force_mavlink1=False))

        # need to wait for server to get the packet and establish the transport
        await asyncio.sleep(0.10)
        server.send_data(pkt.pack(self.mav, force_mavlink1=False))

        # wait for 0.10 sec
        await asyncio.sleep(0.10)

        client.close()
        server.close()

        # Assert the packets were sent
        assert self.cnum == 1
        assert self.snum == 1

    async def test_link_udp_server(self):
        """Test passing data when there's only a server present"""
        server = UDPConnection(rxcallback=self.newpacketcallback,
                               dialect=self.dialect, mavversion=self.version,
                               srcsystem=0, srccomp=0, server=True, name=self.sname)

        await self.loop.create_datagram_endpoint(lambda: server,
                                                 local_addr=(self.ip, self.port))

        # send a mavlink packet:
        pkt = self.mod.MAVLink_heartbeat_message(
            5, 4, 0, 0, 0, int(self.version))
        server.send_data(pkt.pack(self.mav, force_mavlink1=False))

        # wait for 0.10 sec
        await asyncio.sleep(0.10)

        server.close()

        # Assert the packets were not sent
        assert self.snum == 0

    async def test_link_udp_client(self):
        """Test passing data when there's only a client present"""
        client = UDPConnection(rxcallback=self.newpacketcallback,
                               dialect=self.dialect, mavversion=self.version,
                               srcsystem=0, srccomp=0, server=False, name=self.cname)

        try:
            await self.loop.create_datagram_endpoint(lambda: client,
                                                     remote_addr=(self.ip, self.port))
        except ConnectionRefusedError:
            pass  # This is the exception we want

        # send a mavlink packet:
        pkt = self.mod.MAVLink_heartbeat_message(
            5, 4, 0, 0, 0, int(self.version))
        client.send_data(pkt.pack(self.mav, force_mavlink1=False))

        # wait for 0.10 sec
        await asyncio.sleep(0.10)

        client.close()

        # Assert the packets were not sent
        assert self.cnum == 0

    async def test_link_baddata(self):
        """Test passing corrupted data between two udplink connections"""
        client = UDPConnection(rxcallback=self.newpacketcallback,
                               dialect=self.dialect, mavversion=self.version,
                               srcsystem=0, srccomp=0, server=False, name=self.cname)

        server = UDPConnection(rxcallback=self.newpacketcallback,
                               dialect=self.dialect, mavversion=self.version,
                               srcsystem=0, srccomp=0, server=True, name=self.sname)

        await self.loop.create_datagram_endpoint(lambda: server,
                                                 local_addr=(self.ip, self.port))
        await self.loop.create_datagram_endpoint(lambda: client,
                                                 remote_addr=(self.ip, self.port))

        # wait for 0.10 sec
        await asyncio.sleep(0.10)

        # send a mavlink packet each way:
        pkt = self.mod.MAVLink_heartbeat_message(
            5, 4, 0, 0, 0, int(self.version))
        packeddata = pkt.pack(self.mav, force_mavlink1=False)
        corruptdata = b'q837ot4c'
        client.send_data(packeddata + corruptdata)
        await asyncio.sleep(0.0001)
        server.send_data(corruptdata + packeddata)

        # wait for 0.10 sec
        await asyncio.sleep(0.10)

        client.close()
        server.close()

        # Assert only the correct packets were sent
        assert self.cnum == 1
        assert self.snum == 1


if __name__ == '__main__':
    asynctest.main()
