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
    These  routines provide a simplified wrapper for Tkint and some helper functions
    """

    @staticmethod
    def set_text(widget, text: str):
        """ Set the text of a widget """
        if widget.winfo_class() == 'TText' or widget.winfo_class() == 'Text':
            widget.delete("1.0", END)
            widget.insert("1.0", text)
        elif widget.winfo_class() == 'TLabel':
            widget.configure(text=text)
        else:
            widget.delete("0", END)
            widget.insert(0, text)

    @staticmethod
    def get_text(widget) -> str:
        """ Get the text of a widget """
        if widget.winfo_class() == 'TText':
            return widget.cget("text")
        elif widget.winfo_class() == 'TLabel':
            return widget.cget("text")
        else:
            return widget.get()

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
