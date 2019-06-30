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
This contains the console UI.
It:
-Displays tabs for each vehicle DONE
-Enter commands for each vehicle
-Display output from each vehicle DONE
-Able to add/remove tabs/vehicles DONE
-command history ???
-command completion
-Able to switch between tabs DONE
"""
from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window, WindowAlign
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.eventloop import use_asyncio_event_loop
from prompt_toolkit.styles import Style
from prompt_toolkit.layout.processors import BeforeInput

from PaGS.mavlink.pymavutil import mode_toString, getpymavlinkpackage

# Key bindings.
KB = KeyBindings()


def terminal_use_async():
    """
    Tell prompt_toolkit to use asyncio
    """
    use_asyncio_event_loop()


class VehicleTab():
    """
    A tab holding the input and output buffers for a vehicle
    """

    def __init__(self, name, cmdProcessor):
        self.prompt = BeforeInput('MAV>')
        self.input = Buffer(multiline=False, accept_handler=self.handle_action)
        self.output = Buffer(multiline=True)
        self.active = False
        self.name = name
        self.cmdCallback = cmdProcessor

    def handle_action(self, buff):
        """
        Handles any commands from prompt for this vehicle
        """
        #text = buff.text[::-1]
        # Process command?
        self.cmdCallback(self.name, buff.text)
        #self.output_text(text)

    def output_text(self, text: str):
        """
        Send text to output
        """
        #self.output.text += self.prompt.text + str(text) + '\n'
        self.output.insert_text(self.prompt.text + str(text) + '\n')

    def changePrompt(self, prompt: str):
        """
        Change the prompt (mode)
        """
        self.prompt = BeforeInput(prompt + ">")


class Module():
    """
    The terminal UI, based on prompt-toolkit
    """

    def __init__(self, loop, txClbk, vehListClk, vehObjClk, cmdProcessClk, cmdPrint, dialect, mavversion, isGUI):
        self.tabs = []  # all the vehicles, one in each tab

        self.loop = loop

        # Event actions
        self.txCallback = txClbk
        self.vehListCallback = vehListClk
        self.vehObjCallback = vehObjClk
        self.commandProcessor = cmdProcessClk
        self.printer = cmdPrint

        # Mavlink
        self.dialect = dialect
        self.mavversion = mavversion
        self.mod = getpymavlinkpackage(self.dialect, self.mavversion)

        # commands
        self.shortName = "terminal"
        self.commandDict = {'watch': self.watch}

        # Tell prompt_toolkit to use asyncio.
        terminal_use_async()

        self.tabbar = []

        self.style_extensions = {
            # Tabs
            'tabbar':                 'noinherit',
            'tabbar.tab':             '',
            'tabbar.tab.active':      'bold noinherit reverse',
        }

        self.current_style = Style.from_dict(self.style_extensions)

        # make the screen
        self.hscreen = []
        self.hscreen.append(Window(height=1,
                                   content=FormattedTextControl(
                                       self.tabbar, style='class:tabbar'),
                                   align=WindowAlign.LEFT))
        self.hscreen.append(Window(height=1, char='-', style='class:line'))
        self.hscreen.append(Window(content=None))
        self.hscreen.append(Window(height=1, char='-', style='class:line'))
        self.hscreen.append(Window(height=1, content=None))

        self.root_container = HSplit(self.hscreen)
        self.layout = Layout(self.root_container)

        self.application = Application(
            layout=self.layout, key_bindings=KB, full_screen=True, style=self.current_style)

        # event linkages
        self.application.nextTab = self.nextTab

        # initial layout
        self.tabbar.append(
            ('class:tabbar.tab', ' {0} '.format("tmp")))
        self.tabbar.append(('class:tabbar', ' '))
        self.hscreen[0].content = FormattedTextControl(
            self.tabbar, style='class:tabbar')
        self.hscreen[2].content = BufferControl(focusable=False)
        self.hscreen[4].content = BufferControl(focusable=True)

        self.runUI()

    def closeModule(self):
        pass

    def watch(self, veh: str, cmd):
        self.printer(veh, "Watching: " + str(cmd))

    def runUI(self):
        self.application.run_async()

    def changePrompt(self, vehname: str, prompt: str):
        """
        Change the prompt for a vehicle
        """
        for veh in self.tabs:
            if vehname == veh.name:
                veh.changePrompt(prompt)
                self.updateScreen()
                return

    def addVehicle(self, name: str):
        """
        Add a new vehicle tab
        """
        self.tabs.append(VehicleTab(name, self.cmdProcessor))
        self.setActiveTab(name)
        self.application._redraw()

    def cmdProcessor(self, vehname: str, cmd: str):
        """
        Process a user command cmd in tab name
        """
        #self.sendText("I got " + cmd, name)
        self.commandProcessor(vehname, cmd)

    def incomingPacket(self, vehname: str, pkt):
        """
        Incoming packet
        """
        # Send statustext to UI
        if pkt.get_type() == "STATUSTEXT":
            self.printVeh(pkt.text, vehname)
        # Mode change - update prompt
        if pkt.get_type() == "HEARTBEAT":
            self.changePrompt(vehname, mode_toString(pkt, self.mod))
            self.application._redraw()

    def removeVehicleTab(self, name: str):
        """
        Remove a vehicle tab
        """
        for veh in self.tabs:
            if name == veh.name:
                if veh.active:
                    self.nextTab()
                # remove
                self.tabs.remove(veh)
                self.updateScreen()
                return

    def printVeh(self, text: str, name: str):
        """
        Send a string to vehicle <name> output. If <name> is None,
        send to all
        """
        for veh in self.tabs:
            if name is None or veh.name == name:
                veh.output_text(text)

    def print(self, *args):
        """
        Override of the print() function
        """
        for veh in self.tabs:
            line = ""
            for arg in args:
                line += "{}".format(arg)
            veh.output_text(line)

    def updateScreen(self):
        """
        Update the UI after a change
        """
        # generate the tab bar
        self.tabbar = []
        for veh in self.tabs:
            if veh.active:
                self.tabbar.append(
                    ('class:tabbar.tab.active', ' {0} '.format(veh.name)))
            else:
                self.tabbar.append(
                    ('class:tabbar.tab', ' {0} '.format(veh.name)))
            self.tabbar.append(('class:tabbar', ' '))
        self.hscreen[0].content = FormattedTextControl(
            self.tabbar, style='class:tabbar')

        for veh in self.tabs:
            if veh.active:
                self.hscreen[2].content = BufferControl(buffer=veh.output,
                                                        focusable=False)
                self.hscreen[4].content = BufferControl(buffer=veh.input,
                                                        focusable=True,
                                                        input_processors=[veh.prompt])
                return

    def setActiveTab(self, name):
        """
        Set the active vehicle to the named
        """
        for veh in self.tabs:
            if veh.name == name:
                veh.active = True
            else:
                veh.active = False

        self.updateScreen()

    def nextTab(self, reverse=False):
        """
        Navigate to the next tab
        Or previous tab if reverse=True
        """
        hastab = False
        for veh in list(reversed(self.tabs)) if reverse else self.tabs:
            if veh.active:
                hastab = True
            elif hastab:
                self.setActiveTab(veh.name)
                hastab = False
                return
        # if we were at the last tab, circle around to next
        if hastab:
            if reverse:
                self.setActiveTab(self.tabs[-1].name)
            else:
                self.setActiveTab(self.tabs[0].name)
            # self.updateScreen()


@KB.add('c-c')
def _(event):
    " Quit when control-c is pressed. "
    event.app.exit()
    # ensure we break out of the loop.run_forever()
    raise KeyboardInterrupt


@KB.add('c-right')
def _(event):
    """
    Navigate through tabs
    """
    event.app.nextTab()


@KB.add('c-left')
def _(event):
    """
    Navigate through tabs
    """
    event.app.nextTab(True)
