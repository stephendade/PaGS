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
Class for managing all loaded modules
Load module DONE
Unload module DONE
Pass packet events from vehicle DONE
Send packets to vehicles DONE
Events for add/remove vehicle DONE
Hold list of module commands for UI
"""
import logging
import shlex
import traceback
import asyncio
import os
from importlib import import_module
from contextlib import suppress


class moduleManager():
    """
    Manage a set of modules
    """

    def __init__(self, loop, settingsDir, useGUI):
        # dict of modules. Key is module name
        self.multiModules = {}

        # are we using a GUI?
        self.useGUI = useGUI

        # asyncio event loop
        self.loop = loop

        # PaGS settings dir
        self.settingsDir = settingsDir

        # dict of tx send functions for vehicles
        # self.vehTxCallbacks = {}

        # Callback to sending packets
        self.pktTxCallback = None

        # Callback to vehicles
        self.vehListCallback = None
        self.getVehCallback = None

        # Dict of current terminal commands?
        self.commands = {}

        # add in module managment commands
        self.commands['module'] = {'load': self.load, 'list': self.list}

        # Dict of modules that print text
        self.printers = {}

        # WxAsync (if we're using a GUI)
        self.wxApp = None
        self.wxGUITask = None
        self.wxAppPersistMgr = None

        if self.useGUI:
            self.loadGUI()

    def printVeh(self, vehname: str, text: str):
        """
        Print to any loaded outputs
        """
        for prname in self.printers:
            self.printers[prname](text, vehname)

    def onPktTxAttach(self, func):
        """
        Attach a callback to a packet recieved
        """
        self.pktTxCallback = func

    def onVehListAttach(self, func):
        """
        Attach a callback to a packet recieved
        """
        self.vehListCallback = func

    def onVehGetAttach(self, func):
        """
        Attach a callback to a packet recieved
        """
        self.getVehCallback = func

    def load(self, vehname: str, module: str):
        """
        Command handler for "module load xxx" command
        """
        if module in self.multiModules or "PaGS." + module in self.multiModules:
            self.printVeh(vehname, "Module already loaded")
        else:
            try:
                self.addModule(module)
                if module in self.multiModules or "PaGS." + module in self.multiModules:
                    self.printVeh(vehname, "Loaded module " + module)
                else:
                    self.printVeh(vehname, "Cannot load module " + module)
            except ValueError:
                self.printVeh(vehname, "Cannot find module")

    def list(self, vehname: str):
        """
        Command handler for "module list" command
        """
        self.printVeh(vehname, "Loaded Modules: ")
        for key in self.multiModules:
            self.printVeh(vehname, key)

    def onModuleCommandCallback(self, vehname, cmd):
        """
        Process a user command from vehicle
        """
        self.printVeh(vehname, cmd)
        # First decode the command
        if cmd == "":
            return
        try:
            args = shlex.split(cmd)
        except ValueError:
            self.printVeh(vehname, "Malformed command: " + str(cmd))
            return
        # ensure the command is not malformed
        if len(args) < 2 or args[0] not in self.commands.keys() or args[1] not in self.commands[args[0]].keys():
            self.printVeh(vehname, "Command not found: " + str(cmd))
            return
        # ensure the vehicle has a connection
        if not self.getVehCallback(vehname).hasInitial:
            self.printVeh(vehname, "Cannot send command to vehicle - no packets received on link")
            return
        try:
            # then send it onwards, with handled exceptions
            # also await if it's an async function
            if len(args) > 2:
                self.commands[args[0]][args[1]](vehname, *args[2:])
            else:
                self.commands[args[0]][args[1]](vehname)
        except Exception:
            self.printVeh(vehname, traceback.format_exc())

    def loadGUI(self):
        """
        Load WxPython (async)
        """
        from wxasync import WxAsyncApp
        import wx.lib.agw.persist as PM

        self.wxApp = WxAsyncApp()
        self.wxGUITask = asyncio.ensure_future(self.wxApp.MainLoop())

        self.wxAppPersistMgr = PM.PersistenceManager.Get()
        _configFile = os.path.join(
            self.settingsDir, "persistGUI.cfg")
        self.wxAppPersistMgr.SetPersistenceFile(_configFile)

    def addModule(self, name: str):
        """
        Initialise a module
        """
        mod = None
        try:
            mod = import_module(name)
        except ImportError:
            try:
                mod = import_module("PaGS." + name)
                name = "PaGS." + name
            except ImportError:
                raise ValueError('No module with that name')

        self.multiModules[name] = mod.Module(
            self.loop, self.outgoingPacket, self.vehListCallback,
            self.getVehCallback, self.onModuleCommandCallback,
            self.printVeh, self.settingsDir, self.useGUI, self.wxAppPersistMgr)
        # and add any vehicles from beforehand
        for vehname in self.vehListCallback():
            self.multiModules[name].addVehicle(vehname)

        # add any command callbacks
        self.commands[self.multiModules[name].shortName] = {}
        for key, val in self.multiModules[name].commandDict.items():
            self.commands[self.multiModules[name].shortName].update({key: val})

        # add any output printers, if defined
        try:
            printer = self.multiModules[name].printVeh
            self.printers[name] = printer
        except AttributeError:
            pass

    async def removeModule(self, name: str):
        """
        Remove a module
        """
        if name not in self.multiModules:
            raise ValueError('No module with that name')
            return
        else:
            if name in self.printers.keys():
                del self.printers[name]
            del self.commands[self.multiModules[name].shortName]

            await self.multiModules[name].closeModule()

            del self.multiModules[name]
            return

    async def closeAllModules(self):
        """
        Close all modules cleanly
        """
        for modulename in self.multiModules:
            await self.multiModules[modulename].closeModule()

        # Close the wxAsync GUI if required
        if self.wxGUITask:
            self.wxGUITask.cancel()
            with suppress(asyncio.CancelledError):
                await self.wxGUITask  # await for task cancellation

    def addVehicle(self, vehName):
        """
        Event for add new vehicle
        """
        for modulename in self.multiModules:
            self.multiModules[modulename].addVehicle(vehName)

    def removeVehicle(self, vehName):
        """
        Event for remove vehicle
        """
        for modulename in self.multiModules:
            self.multiModules[modulename].removeVehicle(vehName)

    def incomingPacket(self, vehname: str, pkt, strconnection: str):
        """
        Pass incoming packets onto modules
        """
        for modulename in self.multiModules:
            logging.debug("Packet from " + vehname +
                          " going to module " + modulename)
            try:
                # then send it onwards, with handled exceptions
                self.multiModules[modulename].incomingPacket(vehname, pkt)
            except Exception:
                self.printVeh(vehname, traceback.format_exc())

    def outgoingPacket(self, vehname: str, pktType, **kwargs):
        """
        Send the packet out via the vehicle manager
        """
        if self.pktTxCallback:
            logging.debug("Module sending packet to " + vehname)
            self.pktTxCallback(vehname, pktType, **dict(kwargs))
