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

import glob
import logging
import os
import tkinter as ttk
import webbrowser
from tkinter import *
from tkinter.ttk import *
from typing import Dict

from geofinder import CachedDictionary, GeoUtil, AppStyle
from geofinder import TKHelper as Widge


class SetupErrorFrame:
    """
    GUI to display status of GeoCoder install - list missing files
     
    """

    def __init__(self, frame, title, dir_name, cache_filename, error):
        self.logger = logging.getLogger(__name__)
        self.file_error = True
        self.title = title
        self.frame = frame
        self.separator = ":"
        self.dirty_flag = False  # Flag to track if data was modified
        self.error = error

        # Load in list from cache file
        self.directory = dir_name
        self.cache_dir = GeoUtil.get_cache_directory(dir_name)
        self.logger.debug(f'SetupStatusFrame dir={dir_name} sub_dir={self.cache_dir} file={cache_filename}')
        self.cache = CachedDictionary.CachedDictionary(self.cache_dir, cache_filename)
        self.cache.read()
        self.error_dict = {}  # Keep a dictionary of errors

        self.supported_countries_cd = CachedDictionary.CachedDictionary(self.cache_dir, "country_list.pkl")
        self.supported_countries_cd.read()
        self.supported_countries_dct: Dict[str, str] = self.supported_countries_cd.dict

        self.logger.debug(f'country list len={len(self.supported_countries_dct)}')

        self.grd = {"title_label": [0, 0, 5, 5, "W"], "scrollbar": [1, 2, 0, 5, "WNS"], "status": [0, 1, 5, 5, "W"], "add_button": [2, 4, 5, 5, "W"],
                    "listbox": [0, 2, 5, 5, "E"], "unused": [2, 3, 5, 5, "W"], "add_entry": [0, 4, 5, 5, "W"], "load_button": [2, 1, 5, 5, "W"],
                    "geoname_button": [2, 1, 5, 5, "E"], "add_label": [0, 3, 5, 5, "EW"]}

        self.title_label = Widge.CLabel(frame, text=self.title, width=80, style='Info.TLabel')
        self.status = Widge.CLabel(frame, text=" ", width=80, style='Highlight.TLabel')
        self.scrollbar = Scrollbar(frame)
        self.listbox = Listbox(frame, width=80, height=20, bg=AppStyle.LT_GRAY, selectmode=MULTIPLE,
                               yscrollcommand=self.scrollbar.set)
        self.add_button = ttk.Button(frame, text="geonames.org", command=self.web_handler, width=12)


        # Configure buttons and widgets
        self.configure_widgets()

        #self.frame.columnconfigure(0, weight=5)
        #self.frame.columnconfigure(2, weight=2)

        #self.frame.rowconfigure(0, weight=2)
        #self.frame.rowconfigure(1, weight=2)

        # Display data
        self.load_handler()

    @staticmethod
    def web_handler():
        """ Bring up browser with help text """
        help_base = "https://download.geonames.org/export/dump/"
        webbrowser.open(help_base)

    def check_configuration(self, error_dict, country_dct):
        country_file_len = 6
        file_list = ['allCountries.txt', 'cities500.txt']
        self.file_error = False

        # Ensure that there are some geoname data files
        path = os.path.join(self.directory, "*.txt")
        self.logger.info(f'Geoname path {path}')
        count = 0
        alt_found = False

        for filepath in glob.glob(path):
            # Ignore the two Admin files
            fname = os.path.basename(filepath)
            if len(fname) == country_file_len or fname in file_list:
                count += 1
            if fname == 'alternateNamesV2.txt':
                alt_found = True

        if not alt_found:
            # Alternate Names file is missing
            # error_dict["Optional alternateNamesV2.txt not found"] = ""
            self.logger.warning(' alternateNamesV2.txt not found')
            # self.file_error = True

        self.logger.debug(f'geoname file count={count}')
        if count == 0:
            # No data files, add error to error dictionary
            error_dict["Missing Geoname.org  files: e.g AllCountries.txt, alternateNamesV2.txt "] = ""
            self.logger.warning('No Geonames files found')
            self.file_error = True

        if self.file_error:
            self.status.set_text("Download missing from geonames.org and place in {}".format(self.directory))

        # Get country list and validate
        self.logger.debug('load countries')
        # self.supported_countries_cd.read()
        res = self.verify_country_list(country_dct)
        if len(res) > 0:
            error_dict[res] = ''

    def load_handler(self):
        self.check_configuration(self.error_dict, self.supported_countries_dct)

        if len(self.error_dict) > 0:
            # Missing files
            for item in sorted(self.error_dict):
                if len(self.error_dict[item]) > 1:
                    self.listbox.insert(END, "{}:   {}".format(item, self.error_dict[item]))
                else:
                    self.listbox.insert(END, "{}".format(item))
        else:
            self.status.set_text("No configuration errors detected")
            # Load in list and display
            self.listbox.delete(0, END)

    def delete_handler(self):
        # Delete selected items in list
        self.delete_items(self.listbox, self.error_dict)
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
            print(tokens[0])
            dct.pop(tokens[0], None)

        self.load_handler()  # Reload display

    def is_dirty(self):
        # Tells whether the cache was modified
        return self.dirty_flag

    def configure_widgets(self):
        # Grid config for each widget: {name:[col, row, xpad, ypad, sticky]}
        # Create COLUMN 0 widgets
        self.config_grid(self.title_label, "title_label")
        self.config_grid(self.status, "status")

        # Create COLUMN 1 widgets
        self.config_grid(self.listbox, "listbox")
        self.scrollbar.config(command=self.listbox.yview)
        self.config_grid(self.scrollbar, "scrollbar")
        self.config_grid(self.add_button, 'geoname_button')

    @staticmethod
    def verify_country_list(dct):
        if len(dct) == 0:
            return "No countries enabled. Use Countries Tab to add countries"
        elif len(dct) == 1:
            return f"Only {len(dct)} country enabled.  Review in Countries Tab"
        elif len(dct) < 5:
            return f"{len(dct)} countries enabled.  Review in Countries Tab"
        else:
            return ''

    def write(self):
        # Write out cache file
        self.cache.write()

    def config_grid(self, widget, name):
        if self.grd[name][4] == " ":
            widget.grid(row=self.grd[name][1], column=self.grd[name][0], padx=self.grd[name][2], pady=self.grd[name][3])
        else:
            widget.grid(row=self.grd[name][1], column=self.grd[name][0], padx=self.grd[name][2], pady=self.grd[name][3], sticky=self.grd[name][4])
