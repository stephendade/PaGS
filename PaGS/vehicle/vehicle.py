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
Class that stores and manages a single vehicle.
It contains the:
-Working dir
-Vehicle type / Controller DONE
-Vehicle controller version/os
-Current params, wp's, fence and rally points
-Request and store params (retry failed params), write (+validate) param, get specific param (+retry)
-Latest of each packet type DONE
-State of armed/disarmed DONE
-Vehicle mode

It also
-Sends a hearbeat every n sec DONE
-Time since last heartbeat from vehicle. On n sec, goes to no connection DONE

Most of these come in on a incoming packet
"""

import asyncio
import logging
import time
import struct
from contextlib import suppress

from PaGS.mavlink.pymavutil import getpymavlinkpackage


class Vehicle():
    """
    A single vehicle's state
    """

    def __init__(self, loop, name: str, source_system: int, source_component: int,
                 target_system: int, target_component: int, dialect: str, mavversion: float):

        self.loop = loop

        # The latest of each packet type
        self.latestPacketDict = dict()

        # The vehicle
        self.source_system = source_system
        self.source_component = source_component
        self.target_system = target_system
        self.target_component = target_component
        self.dialect = dialect
        self.mavversion = mavversion

        # working folder for this vehicle
        self.folderdir = ""

        # Vehicle name
        self.name = name

        # Mavlink encoder for sending messages
        self.mod = getpymavlinkpackage(self.dialect, self.mavversion)
        self.mav = self.mod.MAVLink(self, srcSystem=source_system,
                                    srcComponent=source_component,
                                    use_native=False)
        self.mav.robust_parsing = True

        # Tx callback to connectionManager
        self.txcallback = None

        # parameters dict. Note all keys are byte arrays
        self.params = dict()
        self.params_type = dict()
        # Status of getting params: [n, total, [got_ids]]
        self.paramstatus = None

        # Waypoints, fence, rally points arrays
        self.waypoints = []
        self.fence = []
        self.rally = []

        # Vehicle strings
        self.fcName = ""  # MAV_AUTOPILOT_ string
        self.fcVersion = ""
        self.OSVersion = ""
        self.vehType = None  # MAV_TYPE_ string

        # Vehicle state
        self.isArmed = None  # True if armed, False if disarmed, None if unknown
        self.flightMode = None  # None is unknown, string MAV_MODE_ otherwise
        self.isConnected = False  # True if getting hb packets

        # Heartbeats (tx and rx)
        self.hbTimeout = 1  # Seconds with no hb packet = no connection
        self.TimeoutTask = asyncio.ensure_future(self.waitrxtimeout())
        self.timeoflasthb = 0  # time of last rx'd hb
        self.hbInterval = 1  # Seconds between hb sending
        self.hbTxTask = asyncio.ensure_future(self.sendHeartbeat())

        # Event linkages for modulemanager
        #self.onPacketRxCallback = None

    # def onPacketRxAttach(self, func):
    #    """
    #    Attach a callback to when a packet is recieved
    #    """
    #    self.onPacketRxCallback = func

    def onPacketTxAttach(self, func):
        """
        Attach a callback to when a packet is transmitted
        """
        self.txcallback = func

    def getPacket(self, pktId: int):
        """
        Get the latest packet of the type ID.
        If the pktId doesn't exist, return None
        """
        if pktId in self.latestPacketDict:
            return self.latestPacketDict[pktId]
        else:
            return None

    def newPacketCallback(self, pkt):
        """
        Called whenever a new unique packet is recived from any current link
        """
        self.latestPacketDict[pkt.id] = pkt
        # print("{0} has packet {1} types".format(self.name, len(self.latestPacketDict)))
        logging.debug("GCS " + self.name + " got " + pkt.get_type())

        # print(pkt.get_header().msgId)

        # if hearbeat, reset timer and get data
        if pkt.get_type() == "HEARTBEAT":
            if not self.isConnected:
                # first packet - send the data stream request
                self.sendPacket(self.mod.MAVLINK_MSG_ID_REQUEST_DATA_STREAM,
                                req_stream_id=self.mod.MAV_DATA_STREAM_ALL,
                                req_message_rate=4,
                                start_stop=1)
            self.isConnected = True
            self.timeoflasthb = time.time()

            # Get FC name and vehicle type
            self.fcName = str(
                self.mod.enums['MAV_AUTOPILOT'][pkt.autopilot].name)
            self.vehType = str(self.mod.enums['MAV_TYPE'][pkt.type].name)

            # Get armed status
            if pkt.base_mode & self.mod.MAV_MODE_FLAG_SAFETY_ARMED:
                self.isArmed = True
            else:
                self.isArmed = False

            # Get flight mode
            self.flightMode = str(pkt.custom_mode)
        # if it's a new param, put it in the dict and update status
        if pkt.get_type() == "PARAM_VALUE":
            # need to convert from bytes to str if required, as mavlink
            # packets have the param name as ascii
            try:
                pkt.param_id = pkt.param_id.decode('ascii')
            except AttributeError:
                pass
            self.params[pkt.param_id.upper()] = round(
                float(pkt.param_value), 6)
            self.params_type[pkt.param_id.upper()] = pkt.param_type
            logging.debug("Got " + str(pkt.param_id.upper()) +
                          " = " + str(pkt.param_value))
            logging.debug("Now have " + str(self.params))
            # if self.paramstatus != True:
            if isinstance(self.paramstatus, (list,)):
                # still downloading params, need to update progress
                self.paramstatus[0] = pkt.param_index
                self.paramstatus[1] = pkt.param_count
                self.paramstatus[2].append(pkt.param_index)

    async def downloadParams(self, timeout=0.5):
        """Request params from vehicle and retry any failed gets. This
        can be awaited or not awaited"""
        self.params = {}
        self.params_type = {}
        self.paramstatus = [0, 0, []]
        self.sendPacket(self.mod.MAVLINK_MSG_ID_PARAM_REQUEST_LIST)
        # wait while getting params
        prevind = 0
        while self.paramstatus[0] < self.paramstatus[1]-1 or self.paramstatus[0] == 0:
            await asyncio.sleep(timeout)
            # is the number of processed params increasing? if not: timeout
            logging.debug("Status: %s", self.paramstatus)
            if prevind >= self.paramstatus[0]:
                self.paramstatus = None
                return False  # Timeout - not getting anything
            prevind = self.paramstatus[0]
        # now get any missed ones
        logging.debug("Status: %s", self.paramstatus)
        if len(self.paramstatus[2]) < self.paramstatus[1]:
            for pid in range(0, self.paramstatus[1]-1):
                if pid not in self.paramstatus[2]:
                    logging.debug("Retrying PID " + str(pid))
                    self.sendPacket(
                        self.mod.MAVLINK_MSG_ID_PARAM_REQUEST_READ, param_id=b'', param_index=pid)
                    await asyncio.sleep(timeout)
        # We're done!
        #print("Got " + len(self.paramstatus[2]) + "params")
        self.paramstatus = True
        return True

    def getParams(self, parm=None):
        """Get the current params, or individual param. Returns None
        if params have not been fully downloaded"""
        if parm and self.paramstatus:
            if parm.upper() in self.params:
                return self.params[parm.upper()]
            else:
                # param does not exist
                return None
        elif self.paramstatus:
            return self.params
        else:
            # not finished downloading parms
            return None

    async def setParam(self, param: str, value, timeout=0.1, retries=3):
        """Set the parameter to the value. Will block until it
        recieves a confirmation from the vehicle or it times out. Can
        be run blocking or non-blocking"""

        # need to ensure we have the full param set first
        if not self.paramstatus:
            logging.debug("Need to get params before setting")
            return False
        if param.upper() not in self.params or param.upper() not in self.params_type:
            logging.debug("Not a valid param")
            return False

        # first need to encode param value
        #paramEnc = 0.0
        if self.params_type[param] == self.mod.MAV_PARAM_TYPE_REAL32 or self.params_type[param] == None:
            paramEnc = float(value)
        elif self.params_type[param] == self.mod.MAV_PARAM_TYPE_UINT8:
            #paramEnc, = struct.unpack(">f", struct.pack(">xxxB", int(value)))
            paramEnc = int(value)
        elif self.params_type[param] == self.mod.MAV_PARAM_TYPE_INT8:
            #paramEnc, = struct.unpack(">f", struct.pack(">xxxb", int(value)))
            paramEnc = int(value)
        elif self.params_type[param] == self.mod.MAV_PARAM_TYPE_UINT16:
            #paramEnc, = struct.unpack(">f", struct.pack(">xxH", int(value)))
            paramEnc = int(value)
        elif self.params_type[param] == self.mod.MAV_PARAM_TYPE_INT16:
            #paramEnc, = struct.unpack(">f", struct.pack(">xxh", int(value)))
            paramEnc = int(value)
        elif self.params_type[param] == self.mod.MAV_PARAM_TYPE_UINT32:
            #paramEnc, = struct.unpack(">f", struct.pack(">I", int(value)))
            paramEnc = int(value)
        elif self.params_type[param] == self.mod.MAV_PARAM_TYPE_INT32:
            #paramEnc, = struct.unpack(">f", struct.pack(">i", int(value)))
            paramEnc = int(value)
        else:
            logging.debug("Not a valid param type")
            return False

        # need to convert to ascii, as mavlink expects ascii
        try:
            paramBytes = param.upper().encode('ascii')
        except AttributeError:
            pass

        # send the packet n times, returning if we succeeded
        for n in range(retries):
            logging.debug("Trying to send " + str(param.upper()))
            #print("Sending " + str(paramEnc))
            self.sendPacket(self.mod.MAVLINK_MSG_ID_PARAM_SET, param_id=paramBytes,
                            param_value=paramEnc, param_type=self.params_type[param.upper()])

            # and now to wait for a reponse
            await asyncio.sleep(timeout)

            # and check, to 6DP
            if self.params[param.upper()] == round(float(value), 6):
                #print("Param updated")
                return True
            #else:
            #    print(
            #        "Param " + str(self.params[param.upper()]) + ", " + str(value))

        # nothing changed
        return False

    async def setHearbeatRate(self, interval: float):
        """Set the heartbeat rate. 0 to disable"""
        if interval > 0:  # restart loop
            await self.stopheartbeat()
            self.hbInterval = interval
            self.hbTxTask = asyncio.ensure_future(self.sendHeartbeat())
        else:
            # disable heartbeat
            await self.stopheartbeat()
            self.hbTxTask = None

    async def setTimeout(self, interval: float):
        """Set the timeout (rx heartbeat) rate. 0 to disable"""
        if interval > 0:  # restart loop
            await self.stoprxtimeout()
            self.hbTimeout = interval
            self.TimeoutTask = asyncio.ensure_future(self.waitrxtimeout())
        else:
            # disable loop
            await self.stoprxtimeout()
            self.TimeoutTask = None

    async def waitrxtimeout(self):
        """Wait for the timeout period. If no hb
        packets recived, then go into timeout"""
        while True:
            try:
                await asyncio.sleep(self.hbTimeout)
                if time.time() > self.timeoflasthb + self.hbTimeout:
                    self.isConnected = False
            except asyncio.TimeoutError:
                pass

    async def sendHeartbeat(self):
        """
        Send a hearbeat packet to the vehicle every period
        """

        while True:
            try:
                await asyncio.sleep(self.hbInterval)
                self.sendPacket(self.mod.MAVLINK_MSG_ID_HEARTBEAT,
                                type=self.mod.MAV_TYPE_GCS,
                                # type=6,
                                autopilot=self.mod.MAV_AUTOPILOT_INVALID,
                                # autopilot=8,
                                base_mode=0,
                                custom_mode=0,
                                system_status=0,
                                mavlink_version=3)
            except asyncio.TimeoutError:
                pass

    async def stopheartbeat(self):
        """Close heartbeat task. Must be called before the
        vehicle is closed"""

        if self.hbTxTask:
            self.hbTxTask.cancel()
            with suppress(asyncio.CancelledError):
                await self.hbTxTask  # await for task cancellation

    async def stoprxtimeout(self):
        """Close rx timeout task. Must be called before the
        vehicle is closed"""

        if self.TimeoutTask:
            self.TimeoutTask.cancel()
            with suppress(asyncio.CancelledError):
                await self.TimeoutTask  # await for task cancellation

    def sendPacket(self, pktType, **kwargs):
        """
        Send the packet a smarter way
        pktType is from self.mav.mavlink_map
        """
        # add in the sys/component id if required:
        # Check if the message if targetted
        if 'target_system' in self.mod.mavlink_map[pktType].fieldnames:
            pkt = self.mod.mavlink_map[pktType](
                **dict(kwargs, target_system=0, target_component=0))
        else:
            pkt = self.mod.mavlink_map[pktType](**dict(kwargs))

        # Pack and send the message
        buf = pkt.pack(self.mav, force_mavlink1=False)
        self.mav.seq = (self.mav.seq + 1) % 256
        self.mav.total_packets_sent += 1
        self.mav.total_bytes_sent += len(buf)

        if self.txcallback:
            logging.debug("GCS " + self.name +
                          " sending " + pkt.get_type())
            self.txcallback(buf, self.name)
        else:
            logging.debug("GCS can't send")

        # return the packed bytes for reference
        return buf
