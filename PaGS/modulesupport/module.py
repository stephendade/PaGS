"""
Module Class. Subclass this in your
own modules
"""


class BaseModule():
    """
    Module
    """

    def __init__(self, loop, txClbk, vehListClk, vehObjClk, cmdProcessClk, prntr, settingsDir, isGUI):
        self.txCallback = txClbk
        self.vehListCallback = vehListClk
        self.commandProcessor = cmdProcessClk
        self.vehObj = vehObjClk
        self.printer = prntr
        self.isGUI = isGUI
        self.settingsDir = settingsDir

        self.shortName = None
        self.commandDict = {}

    def getMav(self, name: str):
        """
        Get the mavlink ref from a vehicle
        """
        return self.vehObj(name).mod

    def addVehicle(self, name: str):
        """
        New vehicle added
        """
        pass

    def incomingPacket(self, vehname: str, pkt):
        """
        On new packet
        """
        pass

    def removeVehicle(self, name: str):
        """
        Vehicle removed
        """
        pass

    async def closeModule(self):
        """
        Close down module
        """
        pass
