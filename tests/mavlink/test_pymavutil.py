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

'''Pymavutil tests

Can import any generate dialect from pymavlink, rasing an exception
if that dialet does not exist

'''
import unittest

from PaGS.mavlink.pymavutil import getpymavlinkpackage, mode_toString


class getpymavlinkpackageTest(unittest.TestCase):

    """
    Class to test getpymavlinkpackage
    """

    def setUp(self):
        """Set up some data that is reused in many tests"""
        self.dialects = ['ardupilotmega', 'common', 'standard', 'minimal']
        self.versions = [1.0, 2.0]

    def tearDown(self):
        """Clean up after each test is run"""
        pass

    def test_goodimports(self):
        """Test importing known good modules"""
        for dialect in self.dialects:
            for version in self.versions:
                mod = getpymavlinkpackage(dialect, version)
                assert mod is not None

    def test_badimports(self):
        """test a bad import, ie one that does not exist"""
        try:
            mod = getpymavlinkpackage('bad', 1.0)
        except ValueError as e:
            assert str(e) == 'Incorrect mavlink dialect'

        try:
            mod = getpymavlinkpackage('common', 1.5)
        except ValueError as e:
            assert str(e) == 'Incorrect mavlink version (must be 1.0 or 2.0)'

    def test_modemappings(self):
        """Test the mode_toString() method"""
        mavlink = getpymavlinkpackage('ardupilotmega', 2.0)

        # PX4
        pktIn = mavlink.MAVLink_heartbeat_message(
                mavlink.MAV_TYPE_QUADROTOR, mavlink.MAV_AUTOPILOT_PX4, 0, 0, 0, 2)
        assert mode_toString(pktIn, mavlink) == "MANUAL"
        pktIn = mavlink.MAVLink_heartbeat_message(
                mavlink.MAV_TYPE_QUADROTOR, mavlink.MAV_AUTOPILOT_PX4, 0, 5, 0, 2)
        assert mode_toString(pktIn, mavlink) == "AUTO_RTL"

        # APM:Copter
        pktIn = mavlink.MAVLink_heartbeat_message(
                mavlink.MAV_TYPE_QUADROTOR, mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA, 0, 0, 0, 2)
        assert mode_toString(pktIn, mavlink) == "STABILIZE"
        pktIn = mavlink.MAVLink_heartbeat_message(
                mavlink.MAV_TYPE_QUADROTOR, mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA, 0, 5, 0, 2)
        assert mode_toString(pktIn, mavlink) == "LOITER"

        # APM:Rover
        pktIn = mavlink.MAVLink_heartbeat_message(
                mavlink.MAV_TYPE_GROUND_ROVER, mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA, 0, 0, 0, 2)
        assert mode_toString(pktIn, mavlink) == "MANUAL"
        pktIn = mavlink.MAVLink_heartbeat_message(
                mavlink.MAV_TYPE_GROUND_ROVER, mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA, 0, 10, 0, 2)
        assert mode_toString(pktIn, mavlink) == "AUTO"

        # APM:Sub
        pktIn = mavlink.MAVLink_heartbeat_message(
                mavlink.MAV_TYPE_SUBMARINE, mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA, 0, 0, 0, 2)
        assert mode_toString(pktIn, mavlink) == "STABILIZE"
        pktIn = mavlink.MAVLink_heartbeat_message(
                mavlink.MAV_TYPE_SUBMARINE, mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA, 0, 4, 0, 2)
        assert mode_toString(pktIn, mavlink) == "GUIDED"

        # APM:Plane
        pktIn = mavlink.MAVLink_heartbeat_message(
                mavlink.MAV_TYPE_FIXED_WING, mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA, 0, 0, 0, 2)
        assert mode_toString(pktIn, mavlink) == "MANUAL"
        pktIn = mavlink.MAVLink_heartbeat_message(
                mavlink.MAV_TYPE_FIXED_WING, mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA, 0, 20, 0, 2)
        assert mode_toString(pktIn, mavlink) == "QLAND"

        # APM:Antenna Tracker
        pktIn = mavlink.MAVLink_heartbeat_message(
                mavlink.MAV_TYPE_ANTENNA_TRACKER, mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA, 0, 0, 0, 2)
        assert mode_toString(pktIn, mavlink) == "MANUAL"
        pktIn = mavlink.MAVLink_heartbeat_message(
                mavlink.MAV_TYPE_ANTENNA_TRACKER, mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA, 0, 2, 0, 2)
        assert mode_toString(pktIn, mavlink) == "SCAN"

if __name__ == '__main__':
    unittest.main()
