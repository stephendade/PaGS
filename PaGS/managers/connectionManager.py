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
Class for managing all links
It takes in all data (serial/tcp/udp) from links and
passes it on (via callbacks) to the relevant vehicles
"""
import collections
import asyncio
import logging
from contextlib import suppress

import serial_asyncio

from PaGS.connection.udplink import UDPConnection
from PaGS.connection.tcplink import TCPConnection
from PaGS.connection.seriallink import SerialConnection


class ConnectionManager():
    """
    A manager for managing links<->vehicles
    """

    def __init__(self, loop, dialect: str, mavversion: float,
                 srcsystem: int, srccomp: int, reconnecttimeout: float = 1):
        """init the class"""
        self.dialect = dialect
        self.mavversion = mavversion

        # GCS ID
        self.sourceSystem = srcsystem
        self.sourceComponent = srccomp

        # event attachements
        self.processed_packet = None

        # The last 255 packets a seq numbers
        # Key is vehiclename, val is a deque(maxlen=256) of the data
        self.last255pkts = {}
        self.last255seq = {}

        # All the connections (asyncio sockets)
        # Key is linkname
        # like "udpserver:127.0.0.1:14570"
        # Val is the connection class
        # Val will be None if no current connection
        self.linkdict = {}

        # 2D dict mapping links to vehicles via sysid.
        # Dim1 is the linkname
        # Dim2 is the Vehname
        # Val is the sysID
        # Key = linkname, Val = list of {Key=vehname, Val = sysid}
        self.matrix = {}

        self.loop = loop

        self.reconnecttimeout = reconnecttimeout

        # create a function to try reconnecting all non-connected links
        # once per n seconds
        self.looptask = asyncio.ensure_future(self.reconnectLinks())

    def onPacketAttach(self, func):
        """
        Attach a callback to on-new-packet
        """
        self.processed_packet = func

    async def stoploop(self):
        """Close reconnectlinks task. Must be called before the
        connectionmanager is closed"""

        self.looptask.cancel()
        with suppress(asyncio.CancelledError):
            await self.looptask  # await for task cancellation

        # cleanly close all links
        for strconnection, link in self.linkdict.items():
            if link:
                link.close()

    async def reconnectLinks(self):
        """Keep trying to reconnect any disconnected links"""
        while True:
            try:
                for strconnection, link in self.linkdict.items():
                    if link is None:
                        logging.debug("trying to reconnect: %s",
                                      strconnection)
                        await asyncio.wait_for(self.initLink(strconnection),
                                               self.reconnecttimeout)
                await asyncio.sleep(self.reconnecttimeout)
            except asyncio.TimeoutError:
                pass

    async def initLink(self, strconnection: str):
        """Try initialising a connection. returns True if connection
        was successful, False otherwise"""
        constr = strconnection.split(":")
        newlink = None
        try:
            if constr[0] == "udpserver":
                newlink = UDPConnection(rxcallback=self.incomingPacket,
                                        clcallback=self.closelinkcallback,
                                        dialect=self.dialect,
                                        mavversion=self.mavversion,
                                        server=True,
                                        srcsystem=self.sourceSystem,
                                        srccomp=self.sourceComponent,
                                        name=strconnection)
                trans = self.loop.create_datagram_endpoint(
                    lambda: newlink, local_addr=(constr[1], constr[2]))
                await asyncio.wait_for(trans, timeout=0.2)
            elif constr[0] == "udpclient":
                newlink = UDPConnection(rxcallback=self.incomingPacket,
                                        clcallback=self.closelinkcallback,
                                        dialect=self.dialect,
                                        mavversion=self.mavversion,
                                        server=False,
                                        srcsystem=self.sourceSystem,
                                        srccomp=self.sourceComponent,
                                        name=strconnection)
                trans = self.loop.create_datagram_endpoint(
                    lambda: newlink, remote_addr=(constr[1], constr[2]))
                await asyncio.wait_for(trans, timeout=0.2)
            elif constr[0] == "serial":
                newlink = SerialConnection(rxcallback=self.incomingPacket,
                                           clcallback=self.closelinkcallback,
                                           dialect=self.dialect,
                                           mavversion=self.mavversion,
                                           srcsystem=self.sourceSystem,
                                           srccomp=self.sourceComponent,
                                           name=strconnection)
                trans = serial_asyncio.create_serial_connection(self.loop, lambda: newlink,
                                                                constr[1], int(constr[2]))
                await asyncio.wait_for(trans, timeout=0.2)
            elif constr[0] == "tcpclient":
                newlink = TCPConnection(rxcallback=self.incomingPacket,
                                        clcallback=self.closelinkcallback,
                                        dialect=self.dialect,
                                        mavversion=self.mavversion,
                                        server=False,
                                        srcsystem=self.sourceSystem,
                                        srccomp=self.sourceComponent,
                                        name=strconnection)
                trans = self.loop.create_connection(
                    lambda: newlink, constr[1], int(constr[2]))
                await asyncio.wait_for(trans, timeout=0.2)
            elif constr[0] == "tcpserver":
                newlink = TCPConnection(rxcallback=self.incomingPacket,
                                        clcallback=self.closelinkcallback,
                                        dialect=self.dialect,
                                        mavversion=self.mavversion,
                                        server=True,
                                        srcsystem=self.sourceSystem,
                                        srccomp=self.sourceComponent,
                                        name=strconnection)

                await self.loop.create_server(lambda: newlink, constr[1], int(constr[2]))
            else:
                logging.debug("Bad link type: %s", constr)
                return False
            # ok, we've got a link
            self.linkdict[strconnection] = newlink
            logging.debug("Added link - %s", strconnection)
            return True
        except(OSError, asyncio.TimeoutError):
            logging.debug("Can't connect - %s", strconnection)
            self.linkdict[strconnection] = None
            return False

    async def addVehicleLink(self, vehicle: str, sysid: int, strconnection: str):
        """Add a vehicle with a connection
        strconnection can be "type:IP:Port" or "type:SerialPort:Baud"
        vehicle is a string, sysid is an int
        """
        # Check if we already have that connection
        if strconnection in self.linkdict:
            logging.debug("Already have the connection, mapping to vehicle")
        else:
            constr = strconnection.split(":")
            if len(constr) != 3:
                logging.debug("Incorrect connection string")
                return False

            await self.initLink(strconnection)

        # if it's a new vehicle, add it in the sequence dicts:
        if vehicle not in self.getAllVeh():
            # if vehicle.name not in self.last255pkts:
            self.last255pkts[vehicle] = collections.deque(maxlen=256)
            # if vehicle.name not in self.last255seq:
            self.last255seq[vehicle] = collections.deque(maxlen=256)

        # If it's a new link, add it in
        if strconnection not in self.matrix:
            # And create the matrix entry for this vehicle/link
            tmpdict = {}
            tmpdict[vehicle] = sysid
            self.matrix[strconnection] = tmpdict
        else:
            # It's a new sysid on the existing link
            olddict = self.matrix[strconnection]
            olddict[vehicle] = sysid
            self.matrix[strconnection] = olddict
        return True

    def getAllVeh(self):
        """get a list of all vehicles in connection matrix"""
        allveh = []
        for strconnection, vehdict in self.matrix.items():
            # Iterate through all links and add if not in list
            for vehname, sysid in vehdict.items():
                if vehname not in allveh:
                    allveh.append(vehname)
        return allveh

    async def removeLink(self, link):
        """Remove all connections to a single link"""
        if link in self.linkdict:
            # remove vehicle mappings
            if link in self.matrix:
                del self.matrix[link]
            # close link - if running link
            if self.linkdict[link] is not None:
                self.linkdict[link].close()
            del self.linkdict[link]
            return True
        else:
            return False

    def closelinkcallback(self, strconnection):
        """Callback to close a link when it's crashed"""
        if strconnection in self.linkdict:
            if self.linkdict[strconnection] is not None:
                logging.debug("Closing %s", strconnection)
                self.linkdict[strconnection].close()
                self.linkdict[strconnection] = None

    async def removeVehicle(self, vehicle: str):
        """Remove all links to a single vehicle and remove the vehicle itself"""
        if vehicle in self.getAllVeh():
            del self.last255pkts[vehicle]
            del self.last255seq[vehicle]
            for strconnection, vehdict in self.matrix.items():
                # Iterate through all links
                if vehicle in vehdict:
                    del vehdict[vehicle]
            # close any empty links
            for strconnection, vehdict in self.matrix.items():
                if not vehdict:
                    await self.removeLink(strconnection)
            return True

        return False

    def incomingPacket(self, pkt, linkname: str):
        """we have a mavlink packet from a linkname, and need to send it to the
        vehicle manager's callback"""
        logging.debug("Rx packet unsort %s", linkname)
        # Don't pass on if bad packet
        if pkt.get_type() == 'BAD_DATA':
            return
        try:
            for vehname, sysid in self.matrix[linkname].items():
                if int(pkt._header.srcSystem) == int(sysid):
                    # Check if we've alreay go that packet from a different link
                    if pkt.get_crc() not in self.last255pkts[vehname]:
                        self.last255pkts[vehname].append(pkt.get_crc())
                        self.last255seq[vehname].append(pkt.get_seq())

                        #  Send the packet up to the callback
                        logging.debug("Rx packet %s, %u", linkname, sysid)
                        if self.processed_packet:
                            self.processed_packet(vehname, pkt, linkname)
                        return
                    else:
                        logging.debug(
                            "Got dup rx packet %s, %u", linkname, sysid)
                        return
            logging.debug("no packet for sysid %u", pkt._header.srcSystem)
        except KeyError:
            logging.debug("No link with name %s", linkname)

    def outgoingPacket(self, buf: bytes, vehname: str):
        """send a databuffer from a vehicle to all it's
        current connections"""
        for strconnection, vehdict in self.matrix.items():
            # Iterate through all links
            for vehnamedict, sysid in vehdict.items():
                if vehnamedict == vehname and self.linkdict[strconnection] is not None:
                    # Yes, it's a link to the vehicle
                    logging.debug("Tx packet %s, %s", vehname, strconnection)
                    self.linkdict[strconnection].send_data(buf)
