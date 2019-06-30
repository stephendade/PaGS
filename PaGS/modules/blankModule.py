"""
<Module Description>
"""

class Module():
    """
    <Module Description>
    """
    def __init__(self, loop, txClbk, vehListClk, vehObjClk, cmdProcessClk, prntr, isGUI):
        self.txCallback = txClbk
        self.vehListCallback = vehListClk
        self.vehObjCallback = vehObjClk

        self.shortName = ""
        self.commandDict = {}

    def addVehicle(self, name: str):
        pass

    def incomingPacket(self, vehname: str, pkt):
        pass

    def removeVehicle(self, name: str):
        pass

    def closeModule(self):
        pass


