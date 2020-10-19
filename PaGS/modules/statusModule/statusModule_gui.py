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

import wx
import wx.grid


class StatusGUIFrame(wx.Frame):
    def __init__(self, settingsDir, wxAppPersistMgr):
        wx.Frame.__init__(self, None, title="Status", name="StatusGUI")

        # Create a panel
        self.p = wx.Panel(self)

        # restore size/position
        self._persistMgr = wxAppPersistMgr
        self._persistMgr.RegisterAndRestore(self)

        # create a sizer for vehicles. 1 row per veh
        self.vehSizer = wx.BoxSizer(wx.HORIZONTAL)

        # Dict of rows by veh name
        self.VehRows = {}

        # Dict of status controls. Key is vehname
        # Val is dict of status buttons
        self.vehStats = {}

    def SavePos(self):
        """Event for when the window is closed"""
        self._persistMgr.SaveAndUnregister(self)

    def addVehicle(self, name: str, enums):
        """
        Add a new vehicle row
        """
        self.VehRows[name] = wx.BoxSizer(wx.VERTICAL)
        self.vehStats[name] = {}

        # Add a title
        self.VehRows[name].Add(wx.StaticText(self.p, label=name), 0, wx.CENTER)

        # Now add the text strings
        for key, val in enums.items():
            stat = str(val.name.replace('MAV_SYS_STATUS_SENSOR_', '').replace('MAV_SYS_STATUS_', ''))
            if stat != "ENUM_END":
                self.vehStats[name][key] = wx.StaticText(self.p, label=stat)
                self.vehStats[name][key].Disable()
                self.VehRows[name].Add(self.vehStats[name][key], 0, wx.CENTER)

        # And add in the vehicle column
        self.vehSizer.Add(self.VehRows[name])
        self.p.SetSizer(self.vehSizer)

        # refresh panel
        self.p.Layout()

    def removeVehicle(self, name: str):
        pass

    def updateGUI(self, vehname: str, statuspkt, enums):
        """
        Update the GUI based on the status strings
        """
        present = statuspkt.onboard_control_sensors_present
        enabled = statuspkt.onboard_control_sensors_enabled
        health = statuspkt.onboard_control_sensors_health
        for key, val in enums.items():
            if key in self.vehStats[vehname]:
                if ((present & key) != key):
                    # Not Present
                    self.vehStats[vehname][key].Disable()
                elif ((enabled & key) != key):
                    # Present, not enabled
                    self.vehStats[vehname][key].Enable
                    self.vehStats[vehname][key].SetForegroundColour((0, 0, 0))
                elif ((health & key) != key):
                    # Present, Enabled, not healthy
                    self.vehStats[vehname][key].Enable()
                    self.vehStats[vehname][key].SetForegroundColour((255, 0, 0))
                else:
                    # Healthy
                    self.vehStats[vehname][key].Enable()
                    self.vehStats[vehname][key].SetForegroundColour((0, 255, 0))
