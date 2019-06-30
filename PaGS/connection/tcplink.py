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
Module for defining tcp connections to mavlink
"""
import logging
import socket

from PaGS.connection.mavconnection import MAVConnection


class TCPConnection(MAVConnection):
    """
    A MAVLink TCP connection (server or client)
    """
    def __init__(self, dialect: str, mavversion: float, name: str,
                 srcsystem: int, srccomp: int, rxcallback, server: bool, clcallback=None) -> None:
        MAVConnection.__init__(self, dialect, mavversion, name,
                               srcsystem, srccomp, rxcallback, clcallback)
        self.server = server
        self.transport = None
        #self.listen.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)

    def connection_made(self, transport) -> None:
        logging.debug("Connection made %s", self.name)
        self.transport = transport
        sock = self.transport.get_extra_info('socket')
        sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)

    def data_received(self, data) -> None:
        logging.debug("Rx packet %s", self.name)
        #if 0xFD in data:
        #    print("Got pkt")
        self.processPackets(data)

    def send_data(self, data: bytes) -> None:
        """Send a bytes through the link"""
        try:
            self.transport.write(data)
            logging.debug("Tx packet %s", self.name)
        except AttributeError:
            # no transport - no current connection
            logging.debug("Tx send error %s", self.name)
            if self.closecallback is not None:
                self.closecallback(self.name)
            return

    def close(self):
        if self.transport:
            self.transport.close()
