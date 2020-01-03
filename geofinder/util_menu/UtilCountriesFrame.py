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

from geofinder.util import GridPosition
from geofinder import AppStyle
from util_menu import UtilListboxFrame
from geodata import GeodataFiles, Country


class SetupCountriesFrame(UtilListboxFrame.ListboxFrame):
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
        self.country_dict = {}

        self.pad = ttk.Label(frame, text="", style='Info.TLabel')  # blank padding row

        self.add_label = ttk.Label(frame, text="All Countries - Select countries below to add to supported list and click Add", style='Info.TLabel')
        self.add_button = ttk.Button(frame, text="add", command=self.add_handler, width=UtilListboxFrame.BUTTON_WIDTH)
        self.scrollbar2 = Scrollbar(frame)

        self.listbox_all_countries = ttk.Treeview(frame, style="Plain.Treeview")  # , selectmode="browse")
        self.listbox_all_countries.tag_configure('odd', background=AppStyle.ODD_ROW_COLOR)
        self.listbox_all_countries.tag_configure('even', background='white')

        self.listbox_all_countries["columns"] = ("pre",)
        self.listbox_all_countries.column("#0", width=400, minwidth=100, stretch=tk.NO)
        self.listbox_all_countries.column("pre", width=500, minwidth=50, stretch=tk.NO)
        self.listbox_all_countries.heading("#0", text="Name", anchor=tk.W)
        self.listbox_all_countries.heading("pre", text="Code", anchor=tk.W)

        self.listbox_all_countries.config(yscrollcommand=self.scrollbar2.set)
        self.scrollbar2.config(command=self.listbox_all_countries.yview)

        super().__init__(frame, title, cache_dir, cache_filename)
        self.tree.heading("#0", text="Name", anchor=tk.W)
        self.tree.heading("pre", text="Code", anchor=tk.W)

        self.logger.info('geodatafiles loading')
        self.geoFiles = GeodataFiles.GeodataFiles(dir_name, None, enable_spell_checker=False)
        self.logger.info('  geodatafiles initialized')

        self.load_handler_all()

    def configure_widgets(self, frm):
        super().configure_widgets(frm)

        # Add Lable for allow user to Add to list
        GridPosition.set_grid_position(self.pad, "pad", grd=self.grd)

        # Add Lable for allow user to Add to list
        GridPosition.set_grid_position(self.add_label, "add_label", grd=self.grd)

        # Add Button to allow user to Add to list
        GridPosition.set_grid_position(self.add_button, "add_button", grd=self.grd)

        # Create listbox of countries to add with scrollbar        
        GridPosition.set_grid_position(self.listbox_all_countries, "listbox_all_countries", grd=self.grd)
        self.scrollbar2.config(command=self.listbox_all_countries.yview)
        GridPosition.set_grid_position(self.scrollbar2, "scrollbar2", grd=self.grd)

    def load_handler(self):
        # Load in list and display - Need to Reverse the Key and Val
        self.clear_display_list(self.tree)

        if len(self.dict)==0:
            # Country list is empty.  Hide Remove button and text
            self.remove_button.grid_remove()
            self.status.text= ''
        else:
            self.remove_button.grid()
            self.status.text = 'Highlight items above to remove and click Remove.'

        for key in sorted(self.dict):
            if len(self.dict[key]) > 1:
                self.list_insert(self.tree, f"{self.dict[key]}", f"{key}")
            else:
                self.list_insert(self.tree, f"{key}", '')

    def delete_items(self, tree, dct):
        # Delete any items in the list that the user selected
        items = tree.selection()
        for line in items:
            col1 = self.tree.item(line, "text")
            col2 = self.tree.item(line, 'values')[0]
            dct.pop(col2, None)

        self.load_handler()  # Reload display

    def load_handler_all(self):
        # Load in list of all countries and display
        # self.listbox_all_countries.delete(0, END)
        self.clear_display_list(self.listbox_all_countries)
        self.logger.info('Building country list: {} countries'.format(len(Country.country_dict)))
        for name in sorted(Country.country_dict):
            row = Country.country_dict[name]
            self.list_insert(self.listbox_all_countries, name.lower(), row[0].lower())

    def add_handler(self):
        # Add items user selected to supported list
        # Delete any items in the list that the user selected

        items = self.listbox_all_countries.selection()
        for line in items:
            col1 = self.listbox_all_countries.item(line, "text")
            col2 = self.listbox_all_countries.item(line, 'values')[0]
            print(f"ADD [{col1}]  [{col2}]")

            if len(col2) > 0:
                self.dict[col2.strip(" ")] = col1.strip(" ")  # Add key for entry to dict
            else:
                self.dict[col1.strip(" ")] = " "  # Add key for entry to dict

        super().add_handler()

    def close(self):
        self.geoFiles.close()
