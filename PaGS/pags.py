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

from __future__ import unicode_literals

import asyncio
import argparse
import sys

from concurrent.futures import ThreadPoolExecutor

from PaGS.managers.connectionManager import ConnectionManager
from PaGS.managers.vehicleManager import VehicleManager
from PaGS.managers import moduleManager
from PaGS.connection.seriallink import findserial


class RedirPrint(object):
    """
    This redirects the stdout
    """
    def __init__(self, writefunc):
        self.writefunc = writefunc

    def write(self, message):
        self.writefunc(message)

    def flush(self):
        # this flush method is needed for python 3 compatibility.
        # this handles the flush command by doing nothing.
        # you might want to specify some extra behavior here.
        pass


class pags():
    """
    A single PaGS instance
    """
    def __init__(self, dialect, mav, source_system, source_component, nogui, multi, source, loop, initialModules):
        """
        Start up PaGS
        """

        # logging.basicConfig(level=logging.DEBUG)
        self.loop = loop

        # Start the connection maxtrix
        self.connmtrx = ConnectionManager(self.loop, dialect, mav, source_system, source_component)

        # Dict of vehicles
        self.allvehicles = VehicleManager(self.loop)

        # Module manager
        self.modules = moduleManager.moduleManager(self.loop, not nogui)

        # event links from connmaxtrix -> vehicle manager
        self.connmtrx.onPacketAttach(self.allvehicles.onPacketRecieved)

        # event links from vehicle manager -> connmatrix
        self.allvehicles.onPacketBufTxAttach(self.connmtrx.outgoingPacket)
        asyncio.ensure_future(self.allvehicles.onLinkAddAttach(self.connmtrx.addVehicleLink))
        asyncio.ensure_future(self.allvehicles.onLinkRemoveAttach(self.connmtrx.removeLink))

        # event links from module manager -> vehicle manager
        self.modules.onPktTxAttach(self.allvehicles.send_message)
        self.modules.onVehListAttach(self.allvehicles.get_vehiclelist)
        self.modules.onVehGetAttach(self.allvehicles.get_vehicle)

        # event links vehicle manager -> module manager
        self.allvehicles.onAddVehicleAttach(self.modules.addVehicle)
        self.allvehicles.onRemoveVehicleAttach(self.modules.removeVehicle)
        self.allvehicles.onPacketRxAttach(self.modules.incomingPacket)

        # Need to load initial modules
        for m in initialModules:
            self.modules.addModule(m)

        # redirect stdout to the terminal printer, if loaded
        # Thus print() can be used properly
        if self.modules.multiModules.get('modules.terminalModule'):
            sys.stdout = RedirPrint(self.modules.multiModules.get('modules.terminalModule').print)

        # Single or multi-vehicle?
        if multi != "":
            # TODO: figure out multivehicle parsing file
            pass
        else:
            # Create vehicles and links
            # Each sysID is assumed to be a different vehicle
            # Multiple links with the same sysid will create a multilink vehicle
            for connection in source:
                Vehname = "Veh_" + str(connection)
                cn = connection.split(':')[0] + ":" + connection.split(':')[1] + ":" + connection.split(':')[2]
                asyncio.ensure_future(self.allvehicles.add_vehicle(Vehname, source_system, source_component,
                                      connection.split(':')[3], connection.split(':')[4],
                                      dialect, mav, cn))

    def close(self):
        """
        Cleanly shutdown a pags instance
        """

        # shutdown all the modules
        self.modules.closeAllModules()

        # Shutdown all the running tasks
        for veh in self.allvehicles.get_vehiclelist():
            self.loop.run_until_complete(self.allvehicles.get_vehicle(veh).stopheartbeat())
            self.loop.run_until_complete(self.allvehicles.get_vehicle(veh).stoprxtimeout())

        self.loop.run_until_complete(self.connmtrx.stoploop())


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="MAVLink ground station")
    parser.add_argument("--source",
                        nargs="*",
                        help="Connection in format connectiontype:connectionstr:sys:comp",
                        default=[])
    parser.add_argument("--sitl",
                        nargs="*",
                        help="SITL Instance to connect to, ie --sitl=0, --sitl=1",
                        default=[])
    parser.add_argument(
        "--mav", help="Mavlink Version (1 or 2)", default=2, type=int)
    parser.add_argument(
        "--dialect", default="ardupilotmega", help="MAVLink dialect")
    parser.add_argument("--source-system", dest='source_system', type=int,
                        default=255, help='MAVLink source system for this GCS')
    parser.add_argument("--source-component", dest='source_component', type=int,
                        default=0, help='MAVLink source component for this GCS')
    parser.add_argument("--multi", default="",
                        help="Use connection file for multivehicle")
    parser.add_argument("--nogui", help="Disable useage of a GUI",
                        action="store_true")
    args = parser.parse_args()

    # Start asyncio, if needed
    loop = asyncio.get_event_loop()
    loop.set_default_executor(ThreadPoolExecutor(1000))

    # Any modules to load on startup
    initialModules = ["modules.terminalModule", "modules.paramModule", "modules.modeModule"]

    # Add SITL instances, if any
    for inst in args.sitl:
        try:
            args.source.append("tcpclient:127.0.0.1:" + str(5760 + 10 * int(inst)) + ":1:0")
        except ValueError:
            pass  # it was a string, not an int.

    # If no sitl or source args, default to USB
    if len(args.sitl) == 0 and len(args.source) == 0:
        devices = findserial()
        for dev in devices:
            args.source.append("serial:" + dev + ":" + str(115200) + ":1:0")

    # If no USB devices, goto udp 14550
    if len(args.source) == 0:
        args.source.append("udpserver:127.0.0.1:14550:1:0")

    main = pags(args.dialect, args.mav, args.source_system, args.source_component, args.nogui, args.multi, args.source, loop, initialModules)

    # Enter the asyncio event loop and wait for a
    # ctrl+c to exit
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        main.close()
        for task in asyncio.Task.all_tasks():
            task.cancel()

        loop.close()
