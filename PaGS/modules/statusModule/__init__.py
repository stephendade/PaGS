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
from PaGS.modulesupport.module import BaseModule


class Module(BaseModule):
    """
    GUI and Text interface showing the system status of each vehicle
    """
    def __init__(self, loop, txClbk, vehListClk, vehObjClk, cmdProcessClk, prntr, settingsDir, isGUI, wxAppPersistMgr):
        BaseModule.__init__(self, loop, txClbk, vehListClk, vehObjClk, cmdProcessClk, prntr, settingsDir, isGUI, wxAppPersistMgr)

        # The short name of the module.
        self.shortName = "status"
        self.commandDict = {"status": self.status}

        self.GUITasks = []

        if self.isGUI:
            from PaGS.modules.statusModule.statusModule_gui import StatusGUIFrame
            self.wxAppPersistMgr = wxAppPersistMgr
            self.statusframe = StatusGUIFrame(self.settingsDir, self.wxAppPersistMgr)
            self.statusframe.Show()

    def status(self, vehname: str):
        """
        Show the current status of a vehicle
        """
        # get latest status packet
        statuspkt = self.vehObj(vehname).getPacket("SYS_STATUS")
        if statuspkt:
            present = statuspkt.onboard_control_sensors_present
            enabled = statuspkt.onboard_control_sensors_enabled
            health = statuspkt.onboard_control_sensors_health
            for key, val in self.getMav(vehname).enums['MAV_SYS_STATUS_SENSOR'].items():
                sysString = ""
                if ((present & key) != key):
                    sysString = "Not Present"
                elif ((enabled & key) != key):
                    sysString = "Present, not enabled"
                elif ((health & key) != key):
                    sysString = "Present, Enabled, not healthy"
                else:
                    sysString = "Healthy"
                if ((present & key) == key):
                    self.printer(vehname, str(val.name.replace('MAV_SYS_STATUS_SENSOR_', '').replace('MAV_SYS_STATUS_', '')) + ": " + sysString)
        else:
            self.printer(vehname, "No status packets recieved yet")

    def addVehicle(self, name: str):
        """
        Called by PaGS when a new vehicle is added
        """
        if self.isGUI:
            self.statusframe.addVehicle(name, self.getMav(name).enums['MAV_SYS_STATUS_SENSOR'])

    def incomingPacket(self, vehname: str, pkt):
        """
        Called by PaGS when a decoded valid MAVLink packet is recieved from a vehicle
        """
        if pkt.get_type() == "SYS_STATUS" and self.isGUI:
            self.statusframe.updateGUI(vehname, pkt, self.getMav(vehname).enums['MAV_SYS_STATUS_SENSOR'])

    def removeVehicle(self, name: str):
        """
        Called by PaGS when a vehicle is removed
        """
        pass

    async def closeModule(self):
        """
        Called by PaGS when the module is shut down
        """
        if self.isGUI:
            self.statusframe.SavePos()
