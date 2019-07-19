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

'''Vehicle tests

Can recieive heartbeats and timeout with "no connection" after n seconds
Can send hearbeats at any rate (including None)
Can get vehicle planform and controller name
Can get arming status

'''

import asyncio
import asynctest

from PaGS.mavlink.pymavutil import getpymavlinkpackage
from PaGS.vehicle.vehicle import Vehicle


class VehicleTest(asynctest.TestCase):

    """
    Class to test Vehicle
    """

    def setUp(self):
        """Set up some data that is reused in many tests"""
        self.dialect = 'ardupilotmega'
        self.mavversion = 2.0
        self.source_system = 255
        self.source_component = 0
        self.target_system = 3
        self.target_component = 8

        # This is the "vehicle" to respond to messages
        self.mod = getpymavlinkpackage(self.dialect, self.mavversion)
        self.mavVehicle = self.mod.MAVLink(self, srcSystem=self.target_system,
                                           srcComponent=self.target_component,
                                           use_native=False)
        self.mavVehicle.robust_parsing = True

        self.veh = None

        self.txpackets = []

        self.onNewPackets = []

    def onNewEvent(self, vehName, pkt):
        """Callback for new packet"""
        self.onNewPackets.append(pkt)

    async def tearDown(self):
        """Close down the test"""
        if self.veh:
            await self.veh.stopheartbeat()
            await self.veh.stoprxtimeout()

    def newpacketcallback(self, buf: bytes, vehname: str):
        """Callback when a vehicle sends a packet"""
        self.txpackets.append(buf)

    def paramcallback(self, buf: bytes, vehname: str):
        """Callback when a vehicle sends a packet - for param testing"""
        # if param request, start sending some params
        pkt = self.mavVehicle.parse_char(buf)
        if isinstance(pkt, self.mod.MAVLink_param_request_list_message):
            # send all params (3 of them)
            pkt = self.mod.MAVLink_param_value_message(
                'RC8_MIN', 1100, self.mod.MAV_PARAM_TYPE_REAL32, 3, 0)
            self.veh.newPacketCallback(pkt)
            pkt = self.mod.MAVLink_param_value_message(
                'RC8_TRIM', 1500, self.mod.MAV_PARAM_TYPE_REAL32, 3, 1)
            self.veh.newPacketCallback(pkt)
            pkt = self.mod.MAVLink_param_value_message(
                'RC8_MAX', 1900, self.mod.MAV_PARAM_TYPE_REAL32, 3, 2)
            self.veh.newPacketCallback(pkt)
        # callback for setting a param
        elif isinstance(pkt, self.mod.MAVLink_param_set_message):
            # send back confirmation
            pkt = self.mod.MAVLink_param_value_message(
                pkt.param_id, pkt.param_value, pkt.param_type, 1, 1)
            self.veh.newPacketCallback(pkt)

    def paramcallbackpartial(self, buf: bytes, vehname: str):
        """Callback when a vehicle sends a packet - for param testing"""
        # if param request, start sending some params
        pkt = self.mavVehicle.parse_char(buf)
        if isinstance(pkt, self.mod.MAVLink_param_request_list_message):
            # send all params (3 of them)
            pkt = self.mod.MAVLink_param_value_message(
                'RC8_MIN', 1100, self.mod.MAV_PARAM_TYPE_REAL32, 3, 0)
            self.veh.newPacketCallback(pkt)
            pkt = self.mod.MAVLink_param_value_message(
                'RC8_MAX', 1900, self.mod.MAV_PARAM_TYPE_REAL32, 3, 2)
            self.veh.newPacketCallback(pkt)
        if isinstance(pkt, self.mod.MAVLink_param_request_read_message):
            # get the missing param
            if pkt.param_index == 1:
                pkt = self.mod.MAVLink_param_value_message(
                    'RC8_TRIM', 1500, self.mod.MAV_PARAM_TYPE_REAL32, 3, 1)
                self.veh.newPacketCallback(pkt)

    async def test_vehicle(self):
        """Test vehicle initialises OK"""
        self.veh = Vehicle(self.loop, "VehA", self.source_system, self.source_component,
                           self.target_system, self.target_component, self.dialect, self.mavversion)

        assert self.veh is not None

    # async def test_onPacketCallback(self):
    #    """Test the onPacketCallback works"""
    #    self.veh = Vehicle(self.loop, "VehA", self.source_system, self.source_component,
    #                       self.target_system, self.target_component, self.dialect, self.mavversion)
    #    self.veh.onPacketRxAttach(self.onNewEvent)
    #
    #    pkt = self.mod.MAVLink_heartbeat_message(
    #        self.mod.MAV_TYPE_QUADROTOR, self.mod.MAV_AUTOPILOT_ARDUPILOTMEGA, 0, 0, 0, int(self.mavversion))
    #    self.veh.newPacketCallback(pkt)
    #
    #    await asyncio.sleep(0.01)
    #
    #    assert len(self.onNewPackets) == 1
    #    assert self.onNewPackets[0] == pkt

    async def test_getPacket(self):
        """Test getting a packet"""
        self.veh = Vehicle(self.loop, "VehA", self.source_system, self.source_component,
                           self.target_system, self.target_component, self.dialect, self.mavversion)
        pkt = self.mod.MAVLink_heartbeat_message(
            self.mod.MAV_TYPE_QUADROTOR, self.mod.MAV_AUTOPILOT_ARDUPILOTMEGA, 0, 0, 0, int(self.mavversion))
        self.veh.newPacketCallback(pkt)

        await asyncio.sleep(0.01)

        assert len(self.veh.latestPacketDict) == 1
        assert self.veh.getPacket(self.mod.MAVLINK_MSG_ID_HEARTBEAT) == pkt
        assert self.veh.getPacket(
            self.mod.MAVLINK_MSG_ID_ESC_TELEMETRY_9_TO_12) is None

    async def test_heartbeat(self):
        """Test heatbeat rate and stopping hb task"""
        self.veh = Vehicle(self.loop, "VehA", self.source_system, self.source_component,
                           self.target_system, self.target_component, self.dialect, self.mavversion)
        self.veh.txcallback = self.newpacketcallback

        await self.veh.setHearbeatRate(0.001)
        await asyncio.sleep(0.15)

        # stop for a while - no extra hb emitted
        await self.veh.setHearbeatRate(0)
        await asyncio.sleep(0.01)

        # due to timer jitter, can only test for approx rate
        # Expecting between 4 and 120 hb packets
        assert len(self.txpackets) > 4
        assert len(self.txpackets) < 120

    async def test_noheartbeat(self):
        """Test no hb task ever"""
        self.veh = Vehicle(self.loop, "VehA", self.source_system, self.source_component,
                           self.target_system, self.target_component, self.dialect, self.mavversion)
        self.veh.txcallback = self.newpacketcallback

        await self.veh.setHearbeatRate(0)
        await asyncio.sleep(0.01)

        assert len(self.txpackets) == 0

    async def test_rxheartbeat(self):
        """Test correct rx of hb from vehicle - time of last packet"""
        self.veh = Vehicle(self.loop, "VehA", self.source_system, self.source_component,
                           self.target_system, self.target_component, self.dialect, self.mavversion)
        self.veh.txcallback = self.newpacketcallback
        await self.veh.setTimeout(0.05)

        pkt = self.mod.MAVLink_heartbeat_message(
            self.mod.MAV_TYPE_QUADROTOR, self.mod.MAV_AUTOPILOT_ARDUPILOTMEGA, 0, 0, 0, int(self.mavversion))
        self.veh.newPacketCallback(pkt)

        await asyncio.sleep(0.02)
        assert self.veh.isConnected is True

        await asyncio.sleep(0.10)
        assert self.veh.isConnected is False

    async def test_norxheartbeat(self):
        """Test no rx hb task ever"""
        self.veh = Vehicle(self.loop, "VehA", self.source_system, self.source_component,
                           self.target_system, self.target_component, self.dialect, self.mavversion)

        await self.veh.setTimeout(0)
        await asyncio.sleep(0.01)

        assert self.veh.isConnected is False

    async def test_vehtypename(self):
        """Test correct veh type and gf name from vehicle"""
        self.veh = Vehicle(self.loop, "VehA", self.source_system, self.source_component,
                           self.target_system, self.target_component, self.dialect, self.mavversion)
        self.veh.txcallback = self.newpacketcallback

        pkt = self.mod.MAVLink_heartbeat_message(
            self.mod.MAV_TYPE_QUADROTOR, self.mod.MAV_AUTOPILOT_ARDUPILOTMEGA, 0, 0, 0, int(self.mavversion))
        self.veh.newPacketCallback(pkt)

        assert self.veh.fcName == 3  # "MAV_AUTOPILOT_ARDUPILOTMEGA"
        assert self.veh.vehType == 2  # "MAV_TYPE_QUADROTOR"

    async def test_armmodestatus(self):
        """Test getting of the arming status and mode from heartbeat"""
        self.veh = Vehicle(self.loop, "VehA", self.source_system, self.source_component,
                           self.target_system, self.target_component, self.dialect, self.mavversion)

        assert self.veh.isArmed is None
        assert self.veh.flightMode is None

        pkt = self.mod.MAVLink_heartbeat_message(
            self.mod.MAV_TYPE_QUADROTOR, self.mod.MAV_AUTOPILOT_ARDUPILOTMEGA, self.mod.MAV_MODE_AUTO_DISARMED, 0, 0, int(self.mavversion))
        self.veh.newPacketCallback(pkt)

        assert self.veh.isArmed is False
        assert self.veh.flightMode == 0

        pkt = self.mod.MAVLink_heartbeat_message(
            self.mod.MAV_TYPE_QUADROTOR, self.mod.MAV_AUTOPILOT_ARDUPILOTMEGA, self.mod.MAV_MODE_MANUAL_ARMED, 1, 0, int(self.mavversion))
        self.veh.newPacketCallback(pkt)

        assert self.veh.isArmed is True
        assert self.veh.flightMode == 1

        pkt = self.mod.MAVLink_heartbeat_message(
            self.mod.MAV_TYPE_QUADROTOR, self.mod.MAV_AUTOPILOT_ARDUPILOTMEGA, self.mod.MAV_MODE_MANUAL_DISARMED, 15, 0, int(self.mavversion))
        self.veh.newPacketCallback(pkt)

        assert self.veh.isArmed is False
        assert self.veh.flightMode == 15

    async def test_params_before(self):
        """Test getting of the parameters before downloaded"""
        self.veh = Vehicle(self.loop, "VehA", self.source_system, self.source_component,
                           self.target_system, self.target_component, self.dialect, self.mavversion)

        assert self.veh.getParams('RC8_MAX') is None
        assert self.veh.getParams() is None

    async def test_params_noresponse(self):
        """Test getting of the parameters, no response from vehicle"""
        self.veh = Vehicle(self.loop, "VehA", self.source_system, self.source_component,
                           self.target_system, self.target_component, self.dialect, self.mavversion)
        await self.veh.downloadParams(timeout=0.1)

        assert self.veh.getParams('RC8_MAX') is None
        assert self.veh.getParams() is None

    async def test_get_params(self):
        """Test getting of the parameters, got all. Plus typo"""
        self.veh = Vehicle(self.loop, "VehA", self.source_system, self.source_component,
                           self.target_system, self.target_component, self.dialect, self.mavversion)
        self.veh.txcallback = self.paramcallback
        await self.veh.downloadParams(timeout=0.25)

        assert self.veh.getParams('RC8_MAX') == 1900
        assert self.veh.getParams('RC8_MAXXX') is None

    async def test_get_params_retry(self):
        """Test getting of the parameters, need to retry some"""
        self.veh = Vehicle(self.loop, "VehA", self.source_system, self.source_component,
                           self.target_system, self.target_component, self.dialect, self.mavversion)
        self.veh.txcallback = self.paramcallbackpartial
        await self.veh.downloadParams(timeout=0.25)

        assert self.veh.getParams('RC8_MAX') == 1900
        assert self.veh.getParams('RC8_TRIM') == 1500

    async def test_set_param_no_params(self):
        """Test setting of params if params not downloaded yet"""
        self.veh = Vehicle(self.loop, "VehA", self.source_system, self.source_component,
                           self.target_system, self.target_component, self.dialect, self.mavversion)
        self.veh.txcallback = self.paramcallback

        assert await self.veh.setParam('RC8_MAX', 1800) is False

    async def test_set_param(self):
        """Test setting of param"""
        self.veh = Vehicle(self.loop, "VehA", self.source_system, self.source_component,
                           self.target_system, self.target_component, self.dialect, self.mavversion)
        self.veh.txcallback = self.paramcallback
        await self.veh.downloadParams(timeout=0.25)

        assert await self.veh.setParam('RC8_MAX', 1730) is True
        assert self.veh.getParams('RC8_MAX') == 1730

    def test_sendPacket(self):
        """Assembling a packet"""
        self.veh = Vehicle(self.loop, "VehA", self.source_system, self.source_component,
                           self.target_system, self.target_component, self.dialect, self.mavversion)
        self.veh.txcallback = self.newpacketcallback

        self.veh.sendPacket(self.mod.MAVLINK_MSG_ID_HEARTBEAT,
                            type=self.mod.MAV_TYPE_GCS,
                            autopilot=self.mod.MAV_AUTOPILOT_INVALID,
                            base_mode=0,
                            custom_mode=0,
                            system_status=0,
                            mavlink_version=int(self.mavversion))

        self.veh.sendPacket(self.mod.MAVLINK_MSG_ID_SET_MODE,
                            base_mode=self.mod.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                            custom_mode=5)

        assert len(self.txpackets) == 2

        # Check the correct sysid was attached to the
        # mode change packet. Going by packet indexes
        assert self.txpackets[1][14] == self.target_system


if __name__ == '__main__':
    asynctest.main()
