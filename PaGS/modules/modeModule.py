"""
Module for changing the vehicle's flight mode
-List availaible flight mode for each vehicle
-Change flight mode
-Tell user if flight mode changed

Console only. No GUI
"""
from PaGS.mavlink.pymavutil import mode_toString, allModes, mode_toInt


class Module():
    """
    Set the vehicle's flight mode
    """

    def __init__(self, loop, txClbk, vehListClk, vehObjClk, cmdProcessClk, prntr, isGUI):
        self.txCallback = txClbk
        self.vehListCallback = vehListClk
        self.vehObj = vehObjClk
        self.printer = prntr

        self.shortName = "mode"
        self.commandDict = {"do": self.modeDo,
                            "list": self.listModes,
                            "arm": self.arm,
                            "disarm": self.disarm}

        # for detecting mode change
        self.lastMode = {}

    def modeDo(self, vehname: str, mode: str):
        """
        Set the mode
        """
        # check valid mode string
        if mode.upper() not in allModes(self.vehObj(vehname).vehType, self.vehObj(vehname).fcName, self.vehObj(vehname).mod):
            self.printer(vehname, "No mode: " + mode.upper())
            return
        intMode = mode_toInt(self.vehObj(vehname).vehType, self.vehObj(
            vehname).fcName, mode.upper(), self.vehObj(vehname).mod)
        if intMode == self.vehObj(vehname).flightMode:
            # Already in this mode
            return

        self.txCallback(vehname, self.vehObj(vehname).mod.MAVLINK_MSG_ID_SET_MODE, base_mode=self.vehObj(
            vehname).mod.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, custom_mode=intMode)

    def arm(self, vehname: str):
        """
        Arm the vehicle MAV_CMD_COMPONENT_ARM_DISARM
        """
        self.txCallback(vehname, self.vehObj(vehname).mod.MAVLINK_MSG_ID_COMMAND_LONG,
                        command=self.vehObj(vehname).mod.MAV_CMD_COMPONENT_ARM_DISARM,
                        confirmation=0, param1=1, param2=0, param3=0, param4=0,
                        param5=0, param6=0, param7=0)

    def disarm(self, vehname: str):
        """
        Disarm the vehicle
        """
        self.txCallback(vehname, self.vehObj(vehname).mod.MAVLINK_MSG_ID_COMMAND_LONG,
                        command=self.vehObj(vehname).mod.MAV_CMD_COMPONENT_ARM_DISARM,
                        confirmation=0, param1=0, param2=0, param3=0, param4=0,
                        param5=0, param6=0, param7=0)

    def listModes(self, vehname: str):
        """
        Print all valid modes for the vehicle
        """
        allmodes = allModes(self.vehObj(vehname).vehType, self.vehObj(
            vehname).fcName, self.vehObj(vehname).mod)
        self.printer(vehname, "Valid modes are: " + str(allmodes))

    def addVehicle(self, name: str):
        """
        New vehicle added
        """
        self.lastMode[name] = None

    def incomingPacket(self, vehname: str, pkt):
        """
        On new packet
        """
        # if heartbeat
        if pkt.get_type() == "HEARTBEAT":
            # if mode changed, tell user
            if pkt.custom_mode != self.lastMode[vehname]:
                self.printer(vehname, "Mode changed to: " +
                             str(mode_toString(pkt, self.vehObj(vehname).mod)))
                self.lastMode[vehname] = pkt.custom_mode

    def removeVehicle(self, name: str):
        """
        Vehicle removed
        """
        if name in self.lastMode.keys():
            del self.lastMode[name]

    def closeModule(self):
        pass
