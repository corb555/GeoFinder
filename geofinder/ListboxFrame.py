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
from tkinter import *
from tkinter import ttk
from tkinter.ttk import *

from geofinder import CachedDictionary
from geofinder.Widge import Widge

BUTTON_WIDTH = 6


class ListboxFrame:
    """
     ListboxFrame -  GUI to display and remove lines from a Cached Dictionary
                     Displays a scrolling list box of data with read/write from a CachedDictionary
                     Allows user to delete items from list
                     Defines overall grid layout for derived classes
    """

    def __init__(self, frame, title, dir_name, cache_filename):
        self.logger = logging.getLogger(__name__)
        self.grd = {"title_label": [0, 0, 5, 5, "EW"],
                    "listbox": [0, 1, 5, 5, "EW"], "scrollbar": [1, 1, 0, 5, "WNS"],
                    "status": [0, 2, 5, 5, "EW"], "load_button": [2, 2, 5, 5, "W"], "remove_button": [2, 2, 5, 5, "W"],
                    "add_label": [0, 3, 5, 5, "EW"], "add_button": [2, 3, 5, 5, "W"],
                    "add_entry": [0, 4, 5, 5, "EW"], "listbox_all_countries": [0, 4, 5, 5, "EW"], "scrollbar2": [1, 4, 0, 5, "WNS"],
                    "country_label": [0, 4, 5, 5, "EW"],
                    "country_entry": [0, 5, 5, 5, "W"], "country_button": [2, 5, 5, 5, "W"],
                    }

        self.title = title
        self.frame = frame
        self.separator = "   ::   "
        self.dirty_flag = False  # Flag to track if data was modified

        self.title_label = ttk.Label(self.frame, text=self.title, width=80)
        self.status = ttk.Label(self.frame, text="Highlight items above to remove and click Remove.", width=80)
        self.scrollbar = Scrollbar(self.frame)
        self.listbox = Listbox(self.frame, width=80, height=15, bg='gray92', selectmode=MULTIPLE,
                               yscrollcommand=self.scrollbar.set)
        self.remove_button = ttk.Button(self.frame, text="remove", command=self.delete_handler, width=BUTTON_WIDTH)

        # Load in list from cache file
        self.directory = dir_name
        self.cache = CachedDictionary.CachedDictionary(dir_name, cache_filename)
        self.cache.read()
        self.dict = self.cache.dict
        self.logger.debug(f'{self.title}')

        # Configure buttons and widgets
        self.configure_widgets(frame)

        # Display data
        self.load_handler()

#todo fix disply of global replace db lookup

    def load_handler(self):
        # Load in list and display
        self.listbox.delete(0, END)
        for item in sorted(self.dict):
            if len(self.dict[item]) > 1:
                self.listbox.insert(END, f"{item}{self.separator}{self.dict[item]}")
            else:
                self.listbox.insert(END, f"{item}")

    def delete_handler(self):
        # Delete selected items in list
        self.delete_items(self.listbox, self.dict)
        self.dirty_flag = True

    def add_handler(self):
        # add  item to list
        self.load_handler()  # Reload listbox with new data
        self.dirty_flag = True

    def delete_items(self, lbox, dct):
        # Delete any items in the list that the user selected
        items = lbox.curselection()
        for line in items:
            tokens = lbox.get(line).split(self.separator)
            print(f"delete: [{tokens[0]}]")
            dct.pop(tokens[0], None)

        self.load_handler()  # Reload display

    def is_dirty(self):
        return self.dirty_flag  # Tells whether the cache was modified

    def configure_widgets(self, frm):
        Widge.set_grid_position(self.title_label, "title_label", grd=self.grd)
        Widge.set_grid_position(self.status, "status", grd=self.grd)
        Widge.set_grid_position(self.listbox, "listbox", grd=self.grd)
        self.scrollbar.config(command=self.listbox.yview)
        Widge.set_grid_position(self.scrollbar, "scrollbar", grd=self.grd)
        Widge.set_grid_position(self.remove_button, "remove_button", grd=self.grd)

    def write(self):
        # Write out cache file
        print(f'Write {self.cache.fname}')
        self.cache.write()
