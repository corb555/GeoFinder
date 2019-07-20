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

from geofinder import Country, GeodataFiles, ListboxFrame
from geofinder.Widge import Widge


class SetupCountriesFrame(ListboxFrame.ListboxFrame):
    """
    ListboxAdd is derived from ListboxFrame
    Supports country lists
    Adds support for adding to the list by typing in a new entry

    ListboxFrame Displays a scrolling list box that is based on a CachedDictionary.
    ListboxFrame defines the overall Grid Layout
    """

    def __init__(self, frame, title: str, dir_name: str, cache_dir: str, cache_filename: str):
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f'SetupConfigureCountries dir {dir_name} cache dir {cache_dir} file {cache_filename}')

        self.add_label = ttk.Label(frame, text="Select countries below to add to supported list and click Add")
        self.add_button = ttk.Button(frame, text="add", command=self.add_handler, width=ListboxFrame.BUTTON_WIDTH)
        self.scrollbar2 = Scrollbar(frame)
        self.listbox_all_countries = Listbox(frame, width=80, height=15, bg='gray92', selectmode=MULTIPLE,
                                             yscrollcommand=self.scrollbar2.set)
        self.country_dict = {}
        super().__init__(frame, title, cache_dir, cache_filename)

        self.geoFiles = GeodataFiles.GeodataFiles(dir_name, None)

        self.load_handler_all()

    def configure_widgets(self, frm):
        super().configure_widgets(frm)

        # Add Lable for allow user to Add to list
        Widge.set_grid_position(self.add_label, "add_label", grd=self.grd)

        # Add Button to allow user to Add to list
        Widge.set_grid_position(self.add_button, "add_button", grd=self.grd)

        # Create listbox of countries to add with scrollbar        
        Widge.set_grid_position(self.listbox_all_countries, "listbox_all_countries", grd=self.grd)
        self.scrollbar2.config(command=self.listbox_all_countries.yview)
        Widge.set_grid_position(self.scrollbar2, "scrollbar2", grd=self.grd)

    def load_handler_all(self):
        # Load in list of all countries and display
        self.listbox_all_countries.delete(0, END)
        for name in sorted(Country.country_dict):
            row = Country.country_dict[name]
            self.listbox_all_countries.insert(END, f"{name.lower()}{self.separator}{row[0].lower()}")

    def add_handler(self):
        # Add items user selected to supported list
        items = self.listbox_all_countries.curselection()
        for line in items:
            print(line)
            tokens = self.listbox_all_countries.get(line).split(self.separator)
            print("[{}]  [{}]".format(tokens[0], tokens[1]))

            if len(tokens) > 1:
                self.dict[tokens[1].strip(" ")] = tokens[0].strip(" ")  # Add key for entry to dict
            else:
                self.dict[tokens[0].strip(" ")] = " "  # Add key for entry to dict

        super().add_handler()
