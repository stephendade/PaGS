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
import os

import wx
import wx.grid
import wx.lib.agw.persist as PM
import wx.lib.mixins.listctrl as listmix

from wxasync import WxAsyncApp


def start_gui():
    """start the GUI"""
    return WxAsyncApp()


class EditableListCtrl(wx.ListCtrl, listmix.TextEditMixin):
    ''' TextEditMixin allows any column to be edited. '''

    def __init__(self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.LC_REPORT):
        """Constructor"""
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.TextEditMixin.__init__(self)

        self.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginLabelEdit)
        self.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEndLabelEdit)

        self.paramdata = {}
        self.paramdataCounter = 0

        self.itemDataMap = self.paramdata

    def addItem(self, param, val):
        """add param"""
        self.paramdata[self.paramdataCounter] = (param, val)
        i = self.InsertItem(0, param)
        self.SetItem(i, 1, str(val))

        # for the sorting to work
        self.SetItemData(i, self.paramdataCounter)

        self.paramdataCounter += 1

    def updateItem(self, param, val):
        """update existing param"""
        for key, itm in self.paramdata.items():
            if itm[0] == param:
                self.paramdata[key] = (param, val)
                break

        i = self.FindItem(0, param)

        if i > -1:
            self.SetItem(i, 1, str(val))
            if self.GetItemBackgroundColour(i) == 'MEDIUM SPRING GREEN':
                self.SetItemBackgroundColour(i, 'WHITE')

    def filterText(self, filterText: str):
        """Filter the list by a partial string"""
        # erase list, go through and only add items that fit
        self.DeleteAllItems()

        for key, itm in self.paramdata.items():
            if fnmatch.fnmatch(itm[0], filterText.upper() + "*"):
                i = self.InsertItem(0, itm[0])
                self.SetItem(i, 1, str(itm[1]))
                self.SetItemData(i, key)

        self.SortList()

    def GetListCtrl(self):
        return self

    def OnBeginLabelEdit(self, event):
        """Event handler for colum editing"""
        if event.Column == 0:
            # Don't edit column 0
            event.Veto()

    def OnEndLabelEdit(self, event):
        """Event handler after param GUI edit"""
        rowid = event.GetIndex()
        old_data = self.GetItem(rowid, 1).Text
        new_data = event.GetLabel()

        # validate user entry
        try:
            if float(new_data):
                pass
        except ValueError:  # Issue error and revert to previous data
            wx.MessageBox('Invalid Entry - Must be a number',
                          'Error', wx.OK | wx.ICON_INFORMATION)
            wx.CallLater(10, self.SetItem, rowid, 1, old_data)
            return

        # highlight as edited
        if float(old_data) != float(new_data):
            self.SetItemBackgroundColour(rowid, 'MEDIUM SPRING GREEN')

    def OnCompareItems(self, item1, item2):
        """Compare function for sorting"""
        return self.paramdata[item1][0] > self.paramdata[item2][0]

    def SortList(self):
        """Sort the items in the list control"""
        self.SortItems(self.OnCompareItems)


class VehParamTab(wx.Panel):
    def __init__(self, parent, writeParamCallback, paramValCallback, saveParamCallback, loadParamCallback, vehName):
        wx.Panel.__init__(self, parent)

        self.vehName = vehName

        # Callbacks
        self.writeParamCallback = writeParamCallback
        self.paramValCallback = paramValCallback
        self.saveParamCallback = saveParamCallback
        self.loadParamCallback = loadParamCallback

        # listctrl to hold the param table
        self.list = EditableListCtrl(self, -1)
        self.list.InsertColumn(0, heading='Parameter', width=250)
        self.list.InsertColumn(1, heading='Value', width=100)

        # Filter control
        self.filterText = wx.TextCtrl(self)
        self.filterText.Bind(wx.EVT_TEXT, self.OnFilterTyped)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.filterText, 0, wx.EXPAND)
        self.sizer.Add(self.list, 1, wx.EXPAND)

        # Buttons
        self.writeParamButton = wx.Button(self, -1, "Write Changes")
        self.writeParamButton.Bind(wx.EVT_BUTTON, self.onButtonWrite)
        self.discardChangesButton = wx.Button(self, -1, "Discard Changes")
        self.discardChangesButton.Bind(wx.EVT_BUTTON, self.onButtonDiscard)
        self.saveParamButton = wx.Button(self, -1, "Save Params")
        self.saveParamButton.Bind(wx.EVT_BUTTON, self.onButtonSave)
        self.loadParamButton = wx.Button(self, -1, "Load Params")
        self.loadParamButton.Bind(wx.EVT_BUTTON, self.onButtonLoad)
        self.writeParamButton.Disable()
        self.discardChangesButton.Disable()
        self.saveParamButton.Disable()
        self.loadParamButton.Disable()

        self.hboxUpper = wx.BoxSizer(wx.HORIZONTAL)
        self.hboxLower = wx.BoxSizer(wx.HORIZONTAL)

        self.hboxUpper.Add(self.writeParamButton, 0)
        self.hboxUpper.Add(self.discardChangesButton, 0)
        self.hboxLower.Add(self.saveParamButton, 0)
        self.hboxLower.Add(self.loadParamButton, 0)

        self.sizer.Add(self.hboxUpper, 0)
        self.sizer.Add(self.hboxLower, 0)

        self.SetSizer(self.sizer)

    def GetListCtrl(self):
        return self.list

    def OnFilterTyped(self, event):
        """Handle the filter text control"""
        self.list.filterText(event.GetString())

    def onButtonWrite(self, event):
        """Write the edited params"""
        count = self.list.GetItemCount()
        for row in range(count):
            item = self.list.GetItem(row, col=0)
            newval = self.list.GetItem(row, col=1)
            if self.list.GetItemBackgroundColour(row) == 'MEDIUM SPRING GREEN':
                self.writeParamCallback(
                    self.vehName, item.Text, float(newval.Text))
                self.list.SetItemBackgroundColour(row, 'WHITE')
        # self.Refresh()

    def onButtonDiscard(self, event):
        """Discard any non-written changes"""
        count = self.list.GetItemCount()
        for row in range(count):
            if self.list.GetItemBackgroundColour(row) == 'MEDIUM SPRING GREEN':
                item = self.list.GetItem(row, col=0).Text
                self.list.SetItem(row, 1, str(self.paramValCallback(self.vehName, item)))
                self.list.SetItemBackgroundColour(row, 'WHITE')

    def onButtonSave(self, event):
        """Save params to file"""
        with wx.FileDialog(self, "Save Parameters file", wildcard="Parameters files (*.parm)|*.parm",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:
            fileDialog.SetFilename("parameters.parm")

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind

            # save the current contents in the file
            pathname = fileDialog.GetPath()

            if self.saveParamCallback:
                self.saveParamCallback(self.vehName, pathname)

    def onButtonLoad(self, event):
        """Save params to file"""
        with wx.FileDialog(self, "Load Parameters file", wildcard="Parameters files (*.parm)|*.parm",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind

            # save the current contents in the file
            pathname = fileDialog.GetPath()

            if self.loadParamCallback:
                self.loadParamCallback(self.vehName, pathname)


class ParamGUIFrame(wx.Frame):
    def __init__(self, settingsDir):
        wx.Frame.__init__(self, None, title="Parameters", name="ParamGUI")
        # self.grid = wx.grid.Grid(self, -1)

        # Create a panel and notebook (tabs holder)
        self.p = wx.Panel(self)
        self.nb = wx.Notebook(self.p)

        # restore size/position
        self._persistMgr = PM.PersistenceManager.Get()
        _configFile = os.path.join(
            settingsDir, "persistGUI.cfg")    # getname()
        self._persistMgr.SetPersistenceFile(_configFile)
        self._persistMgr.RegisterAndRestoreAll(self)

        # Set noteboook in a sizer to create the layout
        self.sizer = wx.BoxSizer()
        self.sizer.Add(self.nb, 1, wx.EXPAND)
        self.p.SetSizer(self.sizer)

    def SavePos(self):
        """Event for when the window is closed"""
        self._persistMgr.SaveAndUnregister()
