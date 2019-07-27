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
This is for testing only - it stores any printed-to-console text internally
"""


class Module():
    """
    small test module for the manager tests
    """
    def __init__(self, loop, txClbk, vehListClk, vehObjClk, cmdProcessClk, prntr, settingsDir, isGUI):
        self.txCallback = txClbk
        self.vehListCallback = vehListClk
        self.vehObjCallback = vehObjClk

        self.printedout = {}

        self.shortName = "intprint"
        self.commandDict = {}

    def printVeh(self, text: str, name: str):
        """
        Send any printed text to a dict
        """
        self.printedout[name].append(text)

    def addVehicle(self, name: str):
        self.printedout[name] = []

    def incomingPacket(self, vehname: str, pkt):
        pass

    def removeVehicle(self, name: str):
        del self.printedout[name]

    async def closeModule(self):
        pass
