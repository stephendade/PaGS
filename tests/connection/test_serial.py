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

'''TCPLink tests
Can send and recieve data (client/server)
If a link fails (disconnected) the link should not crash.
'''
import asyncio
import asynctest
import platform
import asyncio.subprocess

import serial_asyncio

from PaGS.connection.seriallink import SerialConnection
from PaGS.connection.tcplink import TCPConnection
from PaGS.mavlink.pymavutil import getpymavlinkpackage


class SerialLinkTest(asynctest.TestCase):

    """
    Class to test SerialLink
    Requires a specifc serial virtual port (socat for Linux, com2tcp for Windows)
    """

    def setUp(self):
        """Set up some data that is reused in many tests"""
        self.dialect = 'ardupilotmega'
        self.version = 2.0
        self.ip = '127.0.0.1'
        self.port = 15001
        self.baud = 115200
        self.cname = 'tcpclient:127.0.0.1:15001'
        self.sname = None

        # For subprocess support under Windows
        if platform.system() == "Windows":
            asyncio.set_event_loop(asyncio.ProactorEventLoop())
            self.loop = asyncio.get_event_loop()
        
        # the serial <-> tcp server process. Will vary depending on OS
        self.serialServer = None

        self.mod = getpymavlinkpackage(self.dialect, self.version)
        self.mav = self.mod.MAVLink(
            self, srcSystem=0, srcComponent=0, use_native=False)
        self.cnum = 0
        self.snum = 0

    async def tearDown(self):
        """Close down the test"""
        if self.serialServer:
            self.serialServer.terminate()
        line = await self.serialServer.stdout.readline()
        print('serialServer: {!r}'.format(line))
        
    def newpacketcallback(self, pkt, strconnection):
        """Callback when a link has a new packet"""
        if pkt.get_type() == 'HEARTBEAT':
            if strconnection == self.cname:
                self.cnum += 1
            elif strconnection == self.sname:
                self.snum += 1

    async def test_link_serial(self):
        """Test passing data between two tcplink connections"""
        
        if platform.system() == "Windows":
            # self.serialServer = subprocess.Popen(['com2tcp.exe', '--ignore-dsr', '--baud', '115200', '--parity', 'e', '\\.\CNCA0', '127.0.0.1', '15001'], stdout=subprocess.PIPE)
            self.serialServer = await asyncio.create_subprocess_shell('com2tcp.exe --ignore-dsr --baud 115200 --parity e \\.\CNCA0 127.0.0.1 15001', stdout=asyncio.subprocess.PIPE)
            print('process started {}'.format(self.serialServer.pid))
            self.sname = 'serial:\\.\CNCA0:115200'
            self.sPort = 'CNCB0'
        elif platform.system() == "Linux":
            # self.serialServer = subprocess.Popen(['socat', '-Dxs', 'pty,link=/tmp/virtualcom0,ispeed=115200,ospeed=115200,raw,waitslave', 'tcp:127.0.0.1:15001'], stdout=subprocess.PIPE)
            self.serialServer = await asyncio.create_subprocess_shell('socat -Dxs pty,link=/home/appveyor/projects/virtualcom0,ispeed=115200,ospeed=115200,raw,waitslave tcp:127.0.0.1:15001', stdout=asyncio.subprocess.PIPE)
            print('process started {}'.format(self.serialServer.pid))
            self.sname = 'serial:/home/appveyor/projects/virtualcom0:115200'
            self.sPort = '/home/appveyor/projects/virtualcom0'
            
        # server = SerialConnection
        server = SerialConnection(rxcallback=self.newpacketcallback,
                               dialect=self.dialect, mavversion=self.version,
                               srcsystem=0, srccomp=0, name=self.sname)
                               
        client = TCPConnection(rxcallback=self.newpacketcallback,
                               dialect=self.dialect, mavversion=self.version,
                               srcsystem=0, srccomp=0, server=True, name=self.cname)
        
        await self.loop.create_server(lambda: client, self.ip, self.port)
        await serial_asyncio.create_serial_connection(self.loop, lambda: server, self.sPort, self.baud)
        
        # send a mavlink packet each way:
        pkt = self.mod.MAVLink_heartbeat_message(
            5, 4, 0, 0, 0, int(self.version))
        client.send_data(pkt.pack(self.mav, force_mavlink1=False))
        server.send_data(pkt.pack(self.mav, force_mavlink1=False))

        # wait for 0.10 sec
        await asyncio.sleep(0.10)

        client.close()
        server.close()

        # Assert the packets were sent
        assert self.cnum == 1
        assert self.snum == 1


if __name__ == '__main__':
    asynctest.main()
