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
Class for managing all vehicles

A bit more complex than a dict!
"""

import asyncio

from PaGS.vehicle.vehicle import Vehicle


class VehicleManager():
    """
    Manage a set of vehicle
    """

    def __init__(self, loop):
        # list of current vehicle objects (by-ref) name key
        self.veh_list = {}

        # asyncio event loop
        self.loop = loop

        # Module manager links
        self.add_vehicle_callback = None
        self.remove_vehicle_callback = None
        self.incoming_packet_callback = None  # Packet rx'd by vehicle

        # Connection manager links
        self.add_link = None
        self.remove_link = None
        self.outgoingPacketBuffer = None

    def onAddVehicleAttach(self, func):
        """
        Attach a callback to on-new-vehicle
        """
        self.add_vehicle_callback = func

    def onRemoveVehicleAttach(self, func):
        """
        Attach a callback to removing a vehicle
        """
        self.remove_vehicle_callback = func

    def onPacketRxAttach(self, func):
        """
        Attach a callback to a packet recieved
        """
        self.incoming_packet_callback = func

    def onLinkAddAttach(self, func):
        """
        Attach a callback to add a link
        Args are (vehiclename, strconnection)
        """
        self.add_link = func

    def onLinkRemoveAttach(self, func):
        """
        Attach a callback to remove a link
        Args are (vehiclename)
        """
        self.remove_link = func

    def onPacketBufTxAttach(self, func):
        """
        Attach a callback to transmit a packet buffer
        Args are (vehiclename, buf)
        """
        self.outgoingPacketBuffer = func

    def add_vehicle(self, name: str, source_system: int, source_component: int,
                    target_system: int, target_component: int, dialect: str, mavversion: float, strconnection: str):
        """ Add a new vehicle"""
        if name in self.veh_list:
            raise ValueError('Already a vehicle with that name')
        else:
            self.veh_list[name] = Vehicle(self.loop, name, source_system, source_component,
                                          target_system, target_component, dialect, mavversion)

            # Connect packet RX from vehicle to moduleManager
            # self.veh_list[name].onPacketRxAttach(self.incoming_packet_callback)

            # Connect packet TX from vehicle to connectionManager
            self.veh_list[name].onPacketTxAttach(self.outgoingPacketBuffer)

            # tell the modulemanager
            if self.add_vehicle_callback:
                self.add_vehicle_callback(name)
            # matrix.addVehicleLink(self.VehA.name, self.VehA.target_system, self.linkC)
            if self.add_link:
                #self.add_link(name, target_system, strconnection)
                self.loop.create_task(self.add_link(name, target_system, strconnection))

    def add_extraLink(self, name: str, strconnection: str):
        """
        Add an extra link to an existing vehicle
        """
        if name not in self.veh_list:
            raise ValueError('No vehicle with that name')
        else:
            if self.add_link:
                self.add_link(
                    name, self.veh_list[name].target_system, strconnection)

    async def remove_vehicle(self, name):
        """remove a vehicle"""
        if name not in self.veh_list:
            raise ValueError('No vehicle with that name')
        else:
            # need to stop the co-routines first
            await self.veh_list[name].stopheartbeat()
            await self.veh_list[name].stoprxtimeout()
            del self.veh_list[name]
            # tell the modulemanager
            if self.remove_vehicle_callback:
                self.remove_vehicle_callback(name)
            # remove the link(s)
            if self.remove_link:
                #await self.remove_link(name)
                self.loop.create_task(self.remove_link(name))
                #await t1
                #asyncio.ensure_future(self.remove_link(name), loop=self.loop)

    def send_message(self, name, msgid, **kwargs):
        """transmit a packet id and args to vehicle"""
        if name not in self.veh_list:
            raise ValueError('No vehicle with that name')
        else:
            self.veh_list[name].sendPacket(msgid, **dict(kwargs))

    def get_vehicle(self, name: str):
        """Return a vehicle instance"""
        if name not in self.veh_list:
            raise ValueError('No vehicle with that name')
        else:
            return self.veh_list[name]

    def get_vehiclelist(self):
        """Return a list of all vehicle keys"""
        return list(self.veh_list.keys())

    def onPacketRecieved(self, vehname, pkt, strconnection):
        """Called by connectionManager when we have a new packet"""
        if vehname in self.veh_list:
            self.veh_list[vehname].newPacketCallback(pkt)
            # and send through to the modules
            if self.incoming_packet_callback:
                self.incoming_packet_callback(vehname, pkt, strconnection)
