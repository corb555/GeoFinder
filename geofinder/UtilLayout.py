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
import os
import webbrowser
from tkinter import *
from tkinter import ttk
from tkinter.ttk import *
from typing import List

from geofinder import UtilCountriesFrame, UtilErrorFrame, UtilFeatureFrame, UtilReplaceFrame, ListboxFrame, AppStyle


class UtilLayout:
    def __init__(self, root, directory, cache_dir):
        self.logger = logging.getLogger(__name__)
        self.directory = directory
        self.cache_dir = cache_dir

        self.root = root

    def start_up(self):
        # Setup styles
        self.root.configure(background=AppStyle.BG_COLOR)
        AppStyle.GFStyle()
        self.create_util_widgets()

        # Start up
        self.root.mainloop()  # Loop getting user actions. We are now controlled by user window actions

    def create_util_widgets(self):
        self.root.title("GeoFinder Configuration Utility")
        self.frames: List[Frame] = []
        self.listbox_list: List[ListboxFrame] = []
        self.error = ""

        # Add Multiple tabs
        tab_list = ["Errors", "Countries", "Skip List", "Global Replace", "Features"]
        self.create_tabs(tab_list)

        # Create a frame for each tab:

        # Error Status Tab
        self.logger.debug('=====error frame')
        self.status_list = UtilErrorFrame.SetupErrorFrame(self.frames[0], "Configuration Status",
                                                          self.directory, "errors.pkl", self.error)
        self.listbox_list.append(self.status_list)

        # Country Tab -  (has text entry box to add items)
        self.logger.debug('=====country frame')
        self.country_list = UtilCountriesFrame.SetupCountriesFrame(self.frames[1],
                                                                    "Supported Countries - Load geo data for these countries:",
                                                                   self.directory, self.cache_dir, "country_list.pkl")
        self.listbox_list.append(self.country_list)

        # Skiplist Tab - ListboxFrame (simple list)
        self.logger.debug('=====skiplist frame')
        self.skip_list = ListboxFrame.ListboxFrame(self.frames[2], "Skiplist - Ignore errors for these places",
                                                   self.cache_dir, "skiplist.pkl")
        self.listbox_list.append(self.skip_list)

        # GlobalReplace Tab- ListboxFrame (simple list)
        self.logger.debug('=====gbl replace frame')
        self.replace_list = UtilReplaceFrame.SetupReplaceFrame(self.frames[3], "Global Replace  - Replace these errors",
                                                               self.cache_dir, "global_replace.pkl")
        self.listbox_list.append(self.replace_list)

        # Feature tab
        self.logger.debug('=====Feature frame')
        self.feature_list = UtilFeatureFrame.SetupFeatureFrame(self.frames[4],
                                                                "We will load data for these geoname feature types:",
                                                               self.cache_dir, "feature_list.pkl")
        self.listbox_list.append(self.feature_list)

        # Create Help button below frames
        self.help_button = ttk.Button(self.root, text="help", command=self.help_handler, width=10)
        self.help_button.grid(row=1, column=0, sticky="E", pady=9, padx=8)

        # Create Quit button below frames
        self.quit_button = ttk.Button(self.root, text="quit", command=self.quit_handler, width=10)
        self.quit_button.grid(row=1, column=1, sticky="E", pady=9, padx=8)

        #  write out all cache files
        for item in self.listbox_list:
            item.write()

    def create_tabs(self, tabs_list):
        nb = ttk.Notebook(self.root, style='TNotebook')
        nb.grid(row=0, column=0, columnspan=2, pady=9, padx=8)
        for element in tabs_list:
            frame = Frame()
            nb.add(frame, text=element)
            self.frames.append(frame)

    @staticmethod
    def help_handler():
        """ Bring up browser with help text """
        help_base = "https://github.com/corb555/GeoFinder/wiki/User-Guide"
        webbrowser.open(help_base)

    def quit_handler(self):
        #  write out all cache files
        for item in self.listbox_list:
            item.write()

        if self.country_list.is_dirty() or self.feature_list.is_dirty():
            # Delete geoname.pkl so GeoFinder3 will rebuild it with new country list or feature list
            for fname in ['geodata.db']:
                path = os.path.join(self.cache_dir, fname)
                self.logger.debug(f'Quit - DELETING FILE {path}')
                if os.path.exists(path):
                    os.remove(path)
                else:
                    self.logger.warning(f'Delete file not found {path}')

        self.root.quit()
        sys.exit()
