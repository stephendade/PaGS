"""
<Module Description>
"""
from PaGS.modulesupport.module import BaseModule


class Module(BaseModule):
    """
    <Module Description>
    """
    def __init__(self, loop, txClbk, vehListClk, vehObjClk, cmdProcessClk, prntr, settingsDir, wxapp):
        """
        Called by PaGS when a module is loaded 'module load xxx'
        """
        BaseModule.__init__(self, loop, txClbk, vehListClk, vehObjClk, cmdProcessClk, prntr, settingsDir, wxapp)

        # The short name of the module.
        self.shortName = ""

    def addVehicle(self, name: str):
        """
        Called by PaGS when a new vehicle is added
        """
        pass

    def incomingPacket(self, vehname: str, pkt):
        """
        Called by PaGS when a decoded valid MAVLink packet is recieved from a vehicle
        """
        pass

    def removeVehicle(self, name: str):
        """
        Called by PaGS when a vehicle is removed
        """
        pass

    async def closeModule(self):
        """
        Called by PaGS when the module is shut down
        """
        pass
