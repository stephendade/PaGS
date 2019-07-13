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

"""
Subclass for managing MAVLink connections
"""
import collections
import asyncio
import time
import logging

from PaGS.mavlink.pymavutil import getpymavlinkpackage


class MAVConnection(asyncio.Protocol):
    """
    A MAVLink connection
    """
    def __init__(self, dialect: str, mavversion: float, name: str,
                 srcsystem: int, srccomp: int, rxcallback,
                 clcallback=None) -> None:
        self.sourceSystem = srcsystem
        self.sourceComponent = srccomp
        self.mod = getpymavlinkpackage(dialect, mavversion)
        self.packetsRx = collections.deque()
        self.packetsTx = collections.deque()
        self.mav = self.mod.MAVLink(self, self.sourceSystem,
                                    self.sourceComponent, use_native=False)
        self.mav.robust_parsing = True

        # BW measures for RX, per sysid
        # bytes and time(sec) in measurement period
        self.bytesmeasure = (0, time.time())
        self.bytespersecond = 0

        self.callback = rxcallback
        self.closecallback = clcallback

        # Loss % per sysid

        # BW measures for TX, per sysid

        self.name = name

    def processPackets(self, data):
        """
        When data is recieved on the device, process
        into mavlink packets
        """
        msgList = self.mav.parse_buffer(data)
        if msgList:
            for msg in msgList:
                self.packetsRx.append(msg)
                if self.callback:
                    self.callback(msg, self.name)

    def connection_lost(self, exc):
        logging.debug('Connection Lost - %s', self.name)
        if self.closecallback:
            self.closecallback(self.name)

    def error_received(self, exc):
        """Handle a fatal error on the connection"""
        logging.debug('Error Received - %s - %s', self.name, str(exc))
        if self.closecallback:
            self.closecallback(self.name)

    def updatebandwidth(self, bytelen):
        """
        Update the bandwidth (bytes/sec) measurement by
        taking in the number of new bytes recieved,
        every 5 seconds
        """
        (bytesi, timei) = self.bytesmeasure
        if time.time() - timei > 5:
            # do an update if 5 seconds since last BW update
            self.bytespersecond = int(bytesi / (time.time() - timei))
            self.bytesmeasure = (bytelen, time.time())
        else:
            self.bytesmeasure = (bytesi + bytelen, timei)
