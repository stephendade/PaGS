#!/usr/bin/env python3

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

'''
Integrated tests of the main program

'''
import asyncio
import asynctest

from PaGS.pags import pags


class IntegratedTest(asynctest.TestCase):

    """
    Class to test the full program
    """

    def setUp(self):
        """Set up some data that is reused in many tests"""
        self.dialect = 'ardupilotmega'
        self.version = 2.0
        self.port = 15000
        self.ip = "127.0.0.1"
        
        self.source_system = 255
        self.source_component = 0
        self.nogui = True
        self.multi = None
        self.source = ['tcpclient:127.0.0.1:15000']

    def tearDown(self):
        self.pagsInstance.close()
        
    async def test_pagsNoGUI(self):
        """
        Startup an instance without a GUI
        """
        initModules = []
        self.pagsInstance = pags(self.dialect, self.version, self.source_system, self.source_component, self.nogui, self.multi, self.source, self.loop, initModules)
        
        await asyncio.sleep(0.5)


if __name__ == '__main__':
    asynctest.main()
