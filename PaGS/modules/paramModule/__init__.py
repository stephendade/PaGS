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
Module for reading and writing parameters
You can:
-load params from file
-save params to file
-set params
-view params
-download params from vehicle
"""

import fnmatch
import asyncio
from contextlib import suppress


class Module():
    """
    Module for reading and writing parameters
    """

    def __init__(self, loop, txClbk, vehListClk, vehObjClk, cmdProcessClk, prntr, isGUI):
        self.txCallback = txClbk
        self.vehListCallback = vehListClk
        self.vehObjCallback = vehObjClk
        self.printer = prntr
        self.loop = loop

        self.isGUI = isGUI
        self.GUITasks = []

        self.shortName = "param"
        self.commandDict = {'download': self.startDownParam,
                            'status': self.parmStatus,
                            'show': self.show,
                            'set': self.set,
                            'save': self.save,
                            'load': self.load}

        if self.isGUI:
            from PaGS.modules.paramModule.paramModule_gui import ParamGUIFrame, start_gui

            app = start_gui()
            self.vehTabs = {}
            self.paramframe = ParamGUIFrame()
            self.paramframe.Show()
            app.SetTopWindow(self.paramframe)
            self.GUITasks.append(asyncio.ensure_future(app.MainLoop()))

    def show(self, veh: str, parmname: str):
        """Show a parameter value"""
        if self.vehObjCallback(veh).paramstatus is not True:
            self.printer(veh, "Params not downloaded")
            return
        else:
            found = False
            for p in self.vehObjCallback(veh).params:
                if fnmatch.fnmatch(p, parmname.upper()):
                    self.printer(veh, "{0:<16} {1}".format(
                        p, self.vehObjCallback(veh).params[p]))
                    found = True
            if not found:
                # no param with that name
                self.printer(veh, "No param " + parmname)

    def get(self, veh: str, param: str):
        """get a param value - for GUI only"""
        return self.vehObjCallback(veh).params[param]

    def set(self, veh: str, parmname: str, parmval: float):
        """Set a parameter value"""
        try:
            float(parmval)
        except ValueError:
            self.printer(veh, "Invalid param value")
            return
        if self.vehObjCallback(veh).paramstatus is not True:
            self.printer(veh, "Params not downloaded")
        elif parmname.upper() not in self.vehObjCallback(veh).params:
            self.printer(veh, "No param with that name")
        else:
            asyncio.ensure_future(self.vehObjCallback(
                veh).setParam(parmname.upper(), parmval))

    def save(self, veh: str, filename: str):
        """Save the params to file"""
        if self.vehObjCallback(veh).paramstatus is not True:
            self.printer(veh, "Params not downloaded")
            return
        with open(filename, 'w') as out:
            for p in self.vehObjCallback(veh).params:
                out.write("{0:<16} {1}\n".format(
                    p, self.vehObjCallback(veh).params[p]))
            self.printer(veh, str(len(self.vehObjCallback(veh).params)) + " params saved to " + filename)

    def load(self, veh: str, filename: str):
        """load params from file"""
        if self.vehObjCallback(veh).paramstatus is not True:
            self.printer(veh, "Params not downloaded")
            return
        counter = 0
        with open(filename, 'r') as infile:
            for line in infile:
                line = line.strip()
                lparts = line.split()
                if len(lparts) != 2:
                    self.printer(veh, "Param line not valid: " + line)
                elif lparts[0] not in self.vehObjCallback(veh).params:
                    self.printer(veh, "Invalid param: " + lparts[0])
                else:
                    try:
                        float(lparts[1])
                        self.set(veh, lparts[0], float(lparts[1]))
                        counter += 1
                    except ValueError:
                        self.printer(veh, "Invalid param value: " + lparts[1])
            self.printer(veh, str(counter) + " params loaded from " + filename)

    def startDownParam(self, veh: str):
        """Download the parameters from the vehicle"""
        asyncio.ensure_future(self.vehObjCallback(veh).downloadParams())

    def parmStatus(self, veh: str):
        """Download the parameters from the vehicle"""
        if self.vehObjCallback(veh).paramstatus is None:
            self.printer(veh, "Params not downloaded")
        elif isinstance(self.vehObjCallback(veh).paramstatus, (list,)):
            self.printer(veh, "Downloaded " + str(len(self.vehObjCallback(
                veh).paramstatus[2])) + " of " + str(self.vehObjCallback(veh).paramstatus[1]) + " params")
        else:
            self.printer(
                veh, "Got all (" + str(len(self.vehObjCallback(veh).params)) + ") params")

    def addVehicle(self, vehname: str):
        """New vehicle added"""
        if self.isGUI:
            from PaGS.modules.paramModule.paramModule_gui import VehParamTab
            # add a tab
            self.vehTabs[vehname] = VehParamTab(
                self.paramframe.nb, self.set, self.get, self.save, self.load, vehname)
            self.paramframe.nb.AddPage(self.vehTabs[vehname], vehname)

            # add task to load GUI when full param set available
            self.GUITasks.append(asyncio.ensure_future(self.loadGUI(vehname)))

    def incomingPacket(self, vehname: str, pkt):
        if pkt.get_type() == "PARAM_VALUE" and self.isGUI:
            try:
                pkt.param_id = pkt.param_id.decode('ascii')
            except AttributeError:
                pass
            self.vehTabs[vehname].list.updateItem(pkt.param_id.upper(
            ), self.vehObjCallback(vehname).params[pkt.param_id.upper()])

    def removeVehicle(self, name: str):
        pass

    async def closeModule(self):
        """Shutdown the module"""
        if self.isGUI:
            self.paramframe.SavePos()
        for task in self.GUITasks:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task  # await for task cancellation

    async def loadGUI(self, vehname: str):
        """This function waits for all the params to be downloaded
        and then loads them into the GUI"""
        while True:
            try:
                await asyncio.sleep(0.2)

                if self.vehObjCallback(vehname).paramstatus is True:
                    # erase old list (if it exists)

                    # good to load
                    for p in self.vehObjCallback(vehname).params:
                        self.vehTabs[vehname].list.addItem(
                            p, self.vehObjCallback(vehname).params[p])
                    # finally sort all the items in the list
                    self.vehTabs[vehname].list.SortList()

                    # and enable the buttons
                    self.vehTabs[vehname].writeParamButton.Enable()
                    self.vehTabs[vehname].discardChangesButton.Enable()
                    self.vehTabs[vehname].saveParamButton.Enable()
                    self.vehTabs[vehname].loadParamButton.Enable()
                    return
            except asyncio.TimeoutError:
                pass
