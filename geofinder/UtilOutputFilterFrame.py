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

import logging
from tkinter import ttk
import tkinter as tk

from geofinder import UtilListboxFrame
from geofinder import TKHelper as Widge

default = []


class UtilOutputFilterFrame(UtilListboxFrame.ListboxFrame):
    """
    SetupFeatureList allows users to add or delete items in the Feature List
    The Feature list is the Feature types that we will load from a Geonames.org file.  For example, we will load
    Villages, Squares, Parks, Cemetaries, etc but not load Refineries, Glaciers, and Coral Reefs.
    For details on Feature Types see http://www.geonames.org/export/codes.html
    SetupFeatureList is derived from ListboxFrame:

    ListboxFrame Displays a scrolling list box that is based on a CachedDictionary.
    ListboxFrame defines the overall Grid Layout
    """


    def __init__(self, frame, title, dir_name, cache_filename):
        self.logger = logging.getLogger(__name__)

        # Add these in addition to the standard widgets we inherit from ListBoxFrame
        self.add_button = ttk.Button(frame, text="add", command=self.add_handler, width=UtilListboxFrame.BUTTON_WIDTH)
        self.add_label = Widge.CLabel(frame, text="Enter replacements below and click on Add", style='Info.TLabel')
        self.add_label2 = Widge.CLabel(frame, text="Original:", style='Info.TLabel')
        self.add_entry: Widge.CEntry = Widge.CEntry(frame, text=" orig  ", width=15)  # , style='Info.TLabel')
        self.add_replace: Widge.CEntry = Widge.CEntry(frame, text=" rr  ", width=15)  # , style='Info.TLabel')
        self.add_label3 = Widge.CLabel(frame, text="Replacement:", style='Info.TLabel')

        super().__init__(frame, title, dir_name, cache_filename)

        self.tree.heading("#0", text="Original", anchor=tk.W)
        self.tree.heading("pre", text="Replacement", anchor=tk.W)

        # If dictionary is empty, load in defaults
        if len(self.dict) == 0:
            self.logger.error('Output filter list is empty. loading defaults')
            self.set_default(default)
            self.load_defaults()
            super().add_handler()

    def configure_widgets(self, frm):
        # Add the standard widgets in ListBoxFrame
        super().configure_widgets(frm)

        # Add these in addition to the standard widgets in ListBoxFrame
        # todo - remove set_grid_position and just use element.grid()
        Widge.TKHelper.set_grid_position(self.add_button, "country_button", grd=self.grd)
        Widge.TKHelper.set_grid_position(self.add_label, "country_label", grd=self.grd)
        Widge.TKHelper.set_grid_position(self.add_entry, "country_entry", grd=self.grd)
        Widge.TKHelper.set_grid_position(self.add_replace, "country_entry2", grd=self.grd)
        Widge.TKHelper.set_grid_position(self.add_label2, "country_label2", grd=self.grd)
        Widge.TKHelper.set_grid_position(self.add_label3, "country_label3", grd=self.grd)

    def add_handler(self):
        # Allow user to add an item to list.
        val: str = self.add_entry.get_text()
        val2: str = self.add_replace.get_text()
        self.add_label.configure(style='Info.TLabel')
        self.dict[val] = val2  # Add item to dict
        super().add_handler()

    def load_handler(self):
        # Load in list and display
        self.clear_display_list(self.tree)

        for item in sorted(self.dict):
            self.list_insert(self.tree, item, self.dict[item])
