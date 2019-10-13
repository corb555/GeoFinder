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
from tkinter import ttk, messagebox
from tkinter.ttk import *
from typing import List

from geofinder import UtilCountriesFrame, UtilErrorFrame, UtilFeatureFrame, UtilReplaceFrame, UtilListboxFrame, AppStyle, UtilLanguagesFrame, \
    UtilOutputFilterFrame


class UtilLayout:
    """ Create Configuration utility windows"""
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
        self.listbox_list: List[UtilListboxFrame] = []
        self.error = ""

        # Add Multiple tabs
        tab_list = ["Errors", "Countries", "Skip List", "Global Replace", "Features", "Languages", "Output"]
        self.create_tabs(tab_list)

        # Create a frame for each tab:
        frame = 0

        # Error Status Tab
        self.logger.debug(f'====={tab_list[frame]} frame')
        self.status_list = UtilErrorFrame.SetupErrorFrame(self.frames[frame], "Configuration Status",
                                                          self.directory, "errors.pkl", self.error)
        self.listbox_list.append(self.status_list)
        frame += 1

        # Country Tab -  (has text entry box to add items)
        self.logger.debug(f'====={tab_list[frame]} frame')
        self.country_list = UtilCountriesFrame.SetupCountriesFrame(self.frames[frame],
                                                                    "Supported Countries - Load geo data for these countries:",
                                                                   self.directory, self.cache_dir, "country_list.pkl")
        self.listbox_list.append(self.country_list)
        frame += 1

        # Skiplist Tab - ListboxFrame (simple list)
        self.logger.debug(f'====={tab_list[frame]} frame')
        self.skip_list = UtilListboxFrame.ListboxFrame(self.frames[frame], "Skiplist - Ignore errors for these places",
                                                       self.cache_dir, "skiplist.pkl")
        self.listbox_list.append(self.skip_list)
        frame += 1

        # GlobalReplace Tab- ListboxFrame (simple list)
        self.logger.debug(f'====={tab_list[frame]} frame')
        self.replace_list = UtilReplaceFrame.SetupReplaceFrame(self.frames[frame], "Global Replace  - Replace these errors",
                                                               self.cache_dir, "global_replace.pkl")
        self.listbox_list.append(self.replace_list)
        frame += 1

        # Feature tab
        self.logger.debug(f'====={tab_list[frame]} frame')
        self.feature_list = UtilFeatureFrame.SetupFeatureFrame(self.frames[frame],
                                                                "We will load data for these geoname feature types:",
                                                               self.cache_dir, "feature_list.pkl")
        self.listbox_list.append(self.feature_list)
        frame += 1

        # Languages tab
        self.logger.debug(f'====={tab_list[frame]} frame')
        self.languages_list = UtilLanguagesFrame.UtilLanguagesFrame(self.frames[frame],
                                                                "Load alternate names for these languages:",
                                                                    self.cache_dir, "languages_list.pkl")
        self.listbox_list.append(self.languages_list)
        frame += 1

        # Output tab
        self.logger.debug(f'====={tab_list[frame]} frame')
        self.output_list = UtilOutputFilterFrame.UtilOutputFilterFrame(self.frames[frame],
                                                                "Make the following replacements for text written to the import file",
                                                                       self.cache_dir, "output_list.pkl")
        self.listbox_list.append(self.output_list)
        frame += 1

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

        if self.country_list.is_dirty() or self.feature_list.is_dirty() or self.languages_list.is_dirty():
            # Delete geoname.db so GeoFinder will rebuild it with new country list or feature list
            if messagebox.askyesno('Configuration Changed',  'Do you want to rebuild the database on next startup?'):
                for fname in ['geodata.db']:
                    path = os.path.join(self.cache_dir, fname)
                    self.logger.debug(f'Quit - DELETING FILE {path}')
                    if os.path.exists(path):
                        os.remove(path)
                    else:
                        self.logger.warning(f'Delete file not found {path}')

        self.root.quit()
        sys.exit()
