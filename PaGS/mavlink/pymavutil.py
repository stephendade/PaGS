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
Module to hold helper functions for interfacing with the pymavlink library
"""
from importlib import import_module

def getpymavlinkpackage(dialect: str, version: float) -> str:
    """
    Return an import to the specified mavlink dialect and version
    """
    pkg = 'pymavlink.dialects.'
    if version == 1.0:
        pkg += 'v10.'
    elif version == 2.0:
        pkg += 'v20.'
    else:
        raise ValueError('Incorrect mavlink version (must be 1.0 or 2.0)')
    pkg += dialect

    mod = None
    try:
        mod = import_module(pkg)
    except ImportError:
        raise ValueError('Incorrect mavlink dialect')
    return mod

#----------------------
# Taken from mavutil.py
#----------------------

def mode_toString(pktIn, mavlink):
    """Given a hearbeat packet, get the mode
    string"""
    return mode_mapping(pktIn, mavlink, False)[pktIn.custom_mode]

def mode_toInt(mode: str, mavlink):
    """Given a string mode, give the id
    number"""
    pass

def mode_mapping(pktIn, mavlink, inv: bool):
    '''return dictionary mapping mode names to numbers, or None if unknown'''
    mav_type = pktIn.type
    mav_autopilot = pktIn.autopilot
    if mav_autopilot == mavlink.MAV_AUTOPILOT_PX4:
        return px4_map
    if mav_type is None:
        return None
    map = None
    if mav_type in [mavlink.MAV_TYPE_QUADROTOR,
                    mavlink.MAV_TYPE_HELICOPTER,
                    mavlink.MAV_TYPE_HEXAROTOR,
                    mavlink.MAV_TYPE_OCTOROTOR,
                    mavlink.MAV_TYPE_DODECAROTOR,
                    mavlink.MAV_TYPE_COAXIAL,
                    mavlink.MAV_TYPE_TRICOPTER]:
        map = mode_mapping_acm
    if mav_type == mavlink.MAV_TYPE_FIXED_WING:
        map = mode_mapping_apm
    if mav_type == mavlink.MAV_TYPE_GROUND_ROVER:
        map = mode_mapping_rover
    if mav_type == mavlink.MAV_TYPE_SURFACE_BOAT:
        map = mode_mapping_rover # for the time being
    if mav_type == mavlink.MAV_TYPE_ANTENNA_TRACKER:
        map = mode_mapping_tracker
    if mav_type == mavlink.MAV_TYPE_SUBMARINE:
        map = mode_mapping_sub
    if map is None:
        return None
    if inv:
        inv_map = dict((a, b) for (b, a) in map.items())
        return inv_map
    else:
        return map

mode_mapping_apm = {
    0 : 'MANUAL',
    1 : 'CIRCLE',
    2 : 'STABILIZE',
    3 : 'TRAINING',
    4 : 'ACRO',
    5 : 'FBWA',
    6 : 'FBWB',
    7 : 'CRUISE',
    8 : 'AUTOTUNE',
    10 : 'AUTO',
    11 : 'RTL',
    12 : 'LOITER',
    14 : 'LAND',
    15 : 'GUIDED',
    16 : 'INITIALISING',
    17 : 'QSTABILIZE',
    18 : 'QHOVER',
    19 : 'QLOITER',
    20 : 'QLAND',
    21 : 'QRTL',
    22 : 'QAUTOTUNE',
    }
mode_mapping_acm = {
    0 : 'STABILIZE',
    1 : 'ACRO',
    2 : 'ALT_HOLD',
    3 : 'AUTO',
    4 : 'GUIDED',
    5 : 'LOITER',
    6 : 'RTL',
    7 : 'CIRCLE',
    8 : 'POSITION',
    9 : 'LAND',
    10 : 'OF_LOITER',
    11 : 'DRIFT',
    13 : 'SPORT',
    14 : 'FLIP',
    15 : 'AUTOTUNE',
    16 : 'POSHOLD',
    17 : 'BRAKE',
    18 : 'THROW',
    19 : 'AVOID_ADSB',
    20 : 'GUIDED_NOGPS',
    21 : 'SMART_RTL',
    22 : 'FLOWHOLD',
    23 : 'FOLLOW',
}
mode_mapping_rover = {
    0 : 'MANUAL',
    1 : 'ACRO',
    2 : 'LEARNING',
    3 : 'STEERING',
    4 : 'HOLD',
    5 : 'LOITER',
    10 : 'AUTO',
    11 : 'RTL',
    12 : 'SMART_RTL',
    15 : 'GUIDED',
    16 : 'INITIALISING'
    }

mode_mapping_tracker = {
    0 : 'MANUAL',
    1 : 'STOP',
    2 : 'SCAN',
    10 : 'AUTO',
    16 : 'INITIALISING'
    }

mode_mapping_sub = {
    0: 'STABILIZE',
    1: 'ACRO',
    2: 'ALT_HOLD',
    3: 'AUTO',
    4: 'GUIDED',
    7: 'CIRCLE',
    9: 'SURFACE',
    16: 'POSHOLD',
    19: 'MANUAL',
    }

# map from a PX4 "main_state" to a string; see msg/commander_state.msg
# This allows us to map sdlog STAT.MainState to a simple "mode"
# string, used in DFReader and possibly other places.  These are
# related but distict from what is found in mavlink messages; see
# "Custom mode definitions", below.
mainstate_mapping_px4 = {
    0 : 'MANUAL',
    1 : 'ALTCTL',
    2 : 'POSCTL',
    3 : 'AUTO_MISSION',
    4 : 'AUTO_LOITER',
    5 : 'AUTO_RTL',
    6 : 'ACRO',
    7 : 'OFFBOARD',
    8 : 'STAB',
    9 : 'RATTITUDE',
    10 : 'AUTO_TAKEOFF',
    11 : 'AUTO_LAND',
    12 : 'AUTO_FOLLOW_TARGET',
    13 : 'MAX',
}
