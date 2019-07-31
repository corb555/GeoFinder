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
import tkinter as tk
from tkinter import *
from tkinter import ttk
from tkinter.ttk import *

from geofinder import CachedDictionary, GFStyle
from geofinder import Widge as Widge

BUTTON_WIDTH = 6
# tags to aletrnate colors in list box
odd_tag = ('odd',)
even_tag = ('even',)


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
                    "pad": [0, 3, 5, 5, "EW"],
                    "add_label": [0, 4, 5, 5, "EW"], "add_button": [2, 4, 5, 5, "W"],
                    "add_entry": [0, 5, 5, 5, "EW"], "listbox_all_countries": [0, 5, 5, 5, "EW"], "scrollbar2": [1, 5, 0, 5, "WNS"],
                    "country_label": [0, 5, 5, 5, "EW"],
                    "country_entry": [0, 6, 5, 5, "W"], "country_button": [2, 6, 5, 5, "W"],
                    }

        self.title = title
        self.frame = frame
        self.separator = "   ::   "
        self.dirty_flag = False  # Flag to track if data was modified
        self.odd = False

        self.title_label = Widge.CLabel(self.frame, text=self.title, width=80, style='Info.TLabel')
        self.status = Widge.CLabel(self.frame, text="Highlight items above to remove and click Remove.", width=80, style='Info.TLabel')
        self.scrollbar = Scrollbar(self.frame)

        self.tree = ttk.Treeview(self.frame, style="Plain.Treeview")  # , selectmode="browse")
        self.tree.tag_configure('odd', background=GFStyle.ODD_ROW_COLOR)
        self.tree.tag_configure('even', background='white')

        self.tree["columns"] = ("pre",)
        self.tree.column("#0", width=400, minwidth=100, stretch=tk.NO)
        self.tree.column("pre", width=500, minwidth=50, stretch=tk.NO)
        self.tree.heading("#0", text="Name", anchor=tk.W)
        self.tree.heading("pre", text="  ", anchor=tk.W)

        self.tree.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.tree.yview)

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

    def list_insert(self, tree, col1, col2):
        self.odd = not self.odd
        if self.odd:
            tag = odd_tag
        else:
            tag = even_tag
        tree.insert('', "end", "", text=col1, values=(col2,), tags=tag)

    def clear_display_list(self, tree):
        self.odd = False
        for row in tree.get_children():
            tree.delete(row)

    def load_handler(self):
        # Load in list and display
        self.clear_display_list(self.tree)

        for item in sorted(self.dict):
            if len(self.dict[item]) > 1:
                self.list_insert(self.tree, f"{item}", f"{self.dict[item]}")
            else:
                self.list_insert(self.tree, f"{item}", '')

    def delete_handler(self):
        # Delete selected items in list
        self.delete_items(self.tree, self.dict)
        self.dirty_flag = True

    def add_handler(self):
        # add  item to list
        self.load_handler()  # Reload listbox with new data
        self.dirty_flag = True

    """
    def get_list_selection(self):
        # Get the items the user selected in list (tree)
        col1 = (self.tree.item(self.tree.selection(), "text"))
        col2 = (self.tree.item(self.tree.selection())['values'][0])
        return f'{prefix}, {loc}'
    """

    def delete_items(self, tree, dct):
        # Delete any items in the list that the user selected
        items = tree.selection()
        for line in items:
            col1 = self.tree.item(line, "text")
            # col2 =
            self.logger.debug(f'DEL {col1}')
            dct.pop(col1, None)

        self.load_handler()  # Reload display

    def is_dirty(self):
        return self.dirty_flag  # Tells whether the cache was modified

    def configure_widgets(self, frm):
        Widge.Widge.set_grid_position(self.title_label, "title_label", grd=self.grd)
        Widge.Widge.set_grid_position(self.status, "status", grd=self.grd)
        Widge.Widge.set_grid_position(self.tree, "listbox", grd=self.grd)
        Widge.Widge.set_grid_position(self.scrollbar, "scrollbar", grd=self.grd)
        Widge.Widge.set_grid_position(self.remove_button, "remove_button", grd=self.grd)

    def write(self):
        # Write out cache file
        self.cache.write()
