#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#  Copyright (c) 2019.       Mike Herbert
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA

from tkinter import *
from tkinter import ttk, messagebox
from typing import List, Dict


class Widge:
    """
    These  routines provide helper functions for Tkint including standardized get and set text.
    """

    @staticmethod
    def disable_buttons(button_list: List[ttk.Button]) -> None:
        for button in button_list:
            button.config(state="disabled")

    @staticmethod
    def enable_buttons(button_list: List[ttk.Button]) -> None:
        for button in button_list:
            button.config(state="normal")

    @staticmethod
    def fatal_error(msg: str) -> None:
        """ Fatal error -  Notify user and shutdown """
        messagebox.showerror("Error", msg)
        sys.exit()

    @staticmethod
    def exit_dialog(title, msg):
        if messagebox.askyesno(title, msg):
            sys.exit()

    # todo remove set_grid_postion from listboxframe
    import collections

    GridInfo = collections.namedtuple('GridInfo', 'col row xpad ypad sticky')
    GridDict = Dict[str, GridInfo]

    @staticmethod
    def set_grid_position(widget, name: str, grd: GridDict) -> None:
        """
        Lookup name of the widget in grd and position widget in a Tkinter grid layout using params in grd
        grd is a dictionary and
        each entry is a list of Col, row, xpad, ypad, sticky (optional).
        """
        # grd = {"title": [0, 0, 5, 10, "EW"], "progress": [0, 1, 5, 5, "EW"]}

        if grd[name][4] == " ":
            # No sticky value
            widget.grid(row=grd[name].row, column=grd[name][0], padx=grd[name][2],
                        pady=grd[name][3])
        else:
            widget.grid(row=grd[name][1], column=grd[name][0], padx=grd[name][2],
                        pady=grd[name][3], sticky=grd[name][4])


class CLabel(ttk.Label):
    """
    Have generic set_text and get_text
    """

    def __init__(self, parent, **kwargs):
        ttk.Label.__init__(self, parent, **kwargs)

    def get_text(self) -> str:
        """ Get the text of a widget """
        return self.cget("text")

    def set_text(self, text: str):
        """ Set the text of a widget """
        self.configure(text=text)


class CEntry(ttk.Entry):
    """
    Add support for Undo/Redo to TextEntry on Ctl-Z, shift Ctl-y.
    Have generic set_text and get_text
    """

    def __init__(self, parent, *args, **kwargs):
        ttk.Entry.__init__(self, parent, *args, **kwargs)
        self.changes = [""]
        self.steps = int()
        self.bind("<Control-z>", self.undo)
        self.bind("<Control-y>", self.redo)
        self.bind("<Key>", self.add_changes)

    def insert(self, idx, txt):
        self.changes = [""]
        self.steps = int()
        super().insert(idx, txt)

    def undo(self,  _):
        if self.steps != 0:
            self.steps -= 1
            self.delete(0, END)
            super().insert(END, self.changes[self.steps])

    def redo(self,  _):
        if self.steps < len(self.changes):
            self.delete(0, END)
            super().insert(END, self.changes[self.steps])
            self.steps += 1

    def add_changes(self,  _):
        if self.get() != self.changes[-1]:
            self.changes.append(self.get())
            self.steps += 1

    def set_text(self, text: str):
        """ Set the text of a widget """
        self.delete("0", END)
        self.insert(0, text)

    def get_text(self) -> str:
        """ Get the text of a widget """
        return self.get()


"""
    def add_to_layer(self, layer, command, coords, **kwargs):
        # Add support for Z-Layers.  Add item to specific layer 
        layer_tag = "layer %s" % layer
        if layer_tag not in self._layers: self._layers.append(layer_tag)
        tags = kwargs.setdefault("tags", [])
        tags.append(layer_tag)
        item_id = command(coords, **kwargs)
        self._adjust_layers()
        return item_id

    def _adjust_layers(self):
        # Adjust everything to appropriate layer 
        for layer in sorted(self._layers):
            self.canvas.lift(layer)
"""
