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
import logging

from concurrent.futures import ThreadPoolExecutor

from PaGS.managers.connectionManager import ConnectionManager
from PaGS.managers.vehicleManager import VehicleManager

from PaGS.managers import moduleManager

class RedirPrint(object):
    """
    This redirects the stdout
    """
    def __init__(self, writefunc):
        self.writefunc = writefunc

    def write(self, message):
        self.writefunc(message)

    def flush(self):
        #this flush method is needed for python 3 compatibility.
        #this handles the flush command by doing nothing.
        #you might want to specify some extra behavior here.
        pass

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="MAVLink ground station")
    parser.add_argument("--source",
                        nargs="*",
                        help="Connection in format connectiontype:connectionstr:sys:comp",
                        default=["tcpclient:127.0.0.1:5760:1:0"])
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

    # Start asyncio
    loop = asyncio.get_event_loop()
    loop.set_default_executor(ThreadPoolExecutor(1000))
    
    # logging.basicConfig(level=logging.DEBUG)

    # Start the connection maxtrix
    connmtrx = ConnectionManager(loop, args.dialect, args.mav, args.source_system, args.source_component)

    # Dict of vehicles
    allvehicles = VehicleManager(loop)

    # Module manager
    modules = moduleManager.moduleManager(loop, args.dialect, args.mav, not args.nogui)

    # event links from connmaxtrix -> vehicle manager
    connmtrx.onPacketAttach(allvehicles.onPacketRecieved)

    # event links from vehicle manager -> connmatrix
    allvehicles.onPacketBufTxAttach(connmtrx.outgoingPacket)
    asyncio.ensure_future(allvehicles.onLinkAddAttach(connmtrx.addVehicleLink))
    asyncio.ensure_future(allvehicles.onLinkRemoveAttach(connmtrx.removeLink))

    # event links from module manager -> vehicle manager
    modules.onPktTxAttach(allvehicles.send_message)
    modules.onVehListAttach(allvehicles.get_vehiclelist)
    modules.onVehGetAttach(allvehicles.get_vehicle)

    # event links vehicle manager -> module manager
    allvehicles.onAddVehicleAttach(modules.addVehicle)
    allvehicles.onRemoveVehicleAttach(modules.removeVehicle)
    allvehicles.onPacketRxAttach(modules.incomingPacket)

    # Need to load the terminal UI
    modules.addModule("modules.terminalModule")
    modules.addModule("modules.paramModule")

    # redirect stdout to the terminal printer
    # Thus print() can be used properly
    sys.stdout = RedirPrint(modules.multiModules.get('modules.terminalModule').print)

    # Single or multi-vehicle?
    if args.multi != "":
        # TODO: figure out multivehicle parsing file
        pass
    else:
        # Create vehicles and links
        # Each sysID is assumed to be a different vehicle
        # Multiple links with the same sysid will create a multilink vehicle
        for connection in args.source:
            Vehname = "Veh_" + str(connection.split(':')[3])
            cn = connection.split(
                ':')[0]+":"+connection.split(':')[1]+":"+connection.split(':')[2]
            asyncio.ensure_future(allvehicles.add_vehicle(Vehname, args.source_system, args.source_component,
                                    connection.split(':')[3], connection.split(':')[4],
                                    args.dialect, args.mav, cn))

    # Enter the asyncio event loop and wait for a
    # ctrl+c to exit
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        # shutdown all the modules
        modules.closeAllModules()

        # Shutdown all the running tasks
        for veh in allvehicles.get_vehiclelist():
            loop.run_until_complete(allvehicles.get_vehicle(veh).stopheartbeat())
            loop.run_until_complete(allvehicles.get_vehicle(veh).stoprxtimeout())

        #for veh in allvehicles.get_vehiclelist():
        #    loop.run_until_complete(allvehicles.remove_vehicle(veh))

        loop.run_until_complete(connmtrx.stoploop())

        for task in asyncio.Task.all_tasks():
            task.cancel()

        loop.close()
