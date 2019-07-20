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
import pickle
import webbrowser
from pathlib import Path
from tkinter import *
from tkinter import messagebox
from tkinter import ttk
from tkinter.ttk import *
from typing import List

import CachedDictionary
import GeoKeys
import Geodata
import ListboxFrame
import SetupCountriesFrame
import SetupErrorFrame
import SetupFeatureFrame

try:
    import unidecode
except ModuleNotFoundError:
    print('Unidecode missing.  Please run "PIP3 install unidecode" from command line')


# Setup and modify config for geonames
class ReviewWindow:
    """
    Utilities to edit and configure items for Geofinder
    There are 5 tabs:
    
    Status - overall status
    Skiplist - for deleting items from the skiplist
    Replace - for deleting items from the replace list
    Files - for specifying which geo_name files to use for geoname data
    Countries - List of countries to include 
    
    Setup files/countries  allows users to:
     1. set country list config file.  Only entries for those countries will be read.    "country_list.pkl"
     2. select which geonames.org files to read.  file names are place in config file.   "file_names.pkl"
     3. If the above are changed, the utility deletes the cache file and the main GeoCoder app will rebuild it
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        fmt = "%(levelname)s %(asctime)s %(name)s.%(funcName)s %(lineno)d: %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=fmt)
        self.logger.info('Setup')

        self.directory: str = os.path.join(str(Path.home()), Geodata.Geodata.get_directory_name())

        self.cache_dir = GeoKeys.cache_directory(self.directory)
        self.logger.debug(f'Home dir {self.directory} Sub Dir {self.cache_dir}')
        self.window = Tk()
        self.bg_color: str = "gray92"
        self.style: ttk.Style = ttk.Style()
        self.config: CachedDictionary.CachedDictionary = CachedDictionary.CachedDictionary(self.cache_dir, "config.pkl")
        self.config.read()
        self.frames: List[Frame] = []
        self.listbox_list: List[ListboxFrame] = []
        self.error = ""

        if not os.path.exists(self.directory):
            self.logger.info(f'Creating folder {self.directory}')
            os.makedirs(self.directory)

        # Create App window
        self.create_app_window("GeoFinder Setup")

        # Verify config -  test to see if gedcom file accessible 
        self.get_config()

        # Add Multiple tabs
        tab_list = ["Errors", "Countries", "Skip List", "Global Replace", "Features"]
        self.create_tabs(tab_list)

        # Create a frame for each tab:

        # Error Status Tab
        self.logger.debug('=====error frame')
        self.status_list = SetupErrorFrame.SetupErrorFrame(self.frames[0], "Configuration Status",
                                                           self.directory, "errors.pkl", self.error)
        self.listbox_list.append(self.status_list)

        # Country Tab -  (has text entry box to add items)
        self.logger.debug('=====country frame')

        self.country_list = SetupCountriesFrame.SetupCountriesFrame(self.frames[1],
                                                                    "We will only load geo data for these countries:",
                                                                    self.directory, self.cache_dir, "country_list.pkl")
        self.listbox_list.append(self.country_list)

        # Skiplist Tab - ListboxFrame (simple list)
        self.logger.debug('=====skiplist frame')

        self.skip_list = ListboxFrame.ListboxFrame(self.frames[2], "Skiplist - Ignore these errors",
                                                   self.cache_dir, "skiplist.pkl")
        self.listbox_list.append(self.skip_list)

        # GlobalReplace Tab- ListboxFrame (simple list)
        self.logger.debug('=====glb replace frame')

        self.replace_list = ListboxFrame.ListboxFrame(self.frames[3], "Global Replace  - Replace these errors",
                                                      self.cache_dir, "global_replace.pkl")
        self.listbox_list.append(self.replace_list)

        # Feature tab
        self.logger.debug('=====Feature frame')

        self.feature_list = SetupFeatureFrame.SetupFeatureFrame(self.frames[4],
                                                                "We will only load geo data for these features:",
                                                                self.cache_dir, "feature_list.pkl")
        self.listbox_list.append(self.feature_list)

        # Create Help button below frames
        self.help_button = ttk.Button(self.window, text="help", command=self.help_handler, width=10)
        self.help_button.grid(row=1, column=0, sticky="E", pady=9, padx=8)

        # Create Quit button below frames
        self.quit_button = ttk.Button(self.window, text="exit", command=self.quit_handler, width=10)
        self.quit_button.grid(row=1, column=1, sticky="E", pady=9, padx=8)

        # Start up 
        self.window.mainloop()  # Loop getting user actions. We are now controlled by user window actions

    def create_app_window(self, title):
        self.window.title(title)
        self.window.columnconfigure(0, weight=1)

        self.window.style = ttk.Style()
        self.window.style.theme_use("clam")
        self.window.style.configure('.', font=('Helvetica', 14))
        self.window.configure(bg="gray92")

    def create_tabs(self, tabs_list):
        nb = ttk.Notebook(self.window)
        nb.grid(row=0, column=0, columnspan=2)
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
        # Close all the lists - write out cache files
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

        self.window.quit()
        sys.exit()

    def get_config(self):
        """ Read config file  """
        # Verify main directory exists
        self.logger.debug('get config')
        if not os.path.exists(self.directory):
            self.logger.info(f'Geoname folder not found {self.directory}.  Creating')
            os.makedirs(self.directory)

        path = self.cache_dir
        if not os.path.exists(path):
            self.logger.info(f'Data folder not found {path}.  Creating')

            os.makedirs(path)

            # Create empty config file
            path = os.path.join(self.cache_dir, "config.pkl")
            self.logger.info(f'Creating config pickle file {path}.')

            self.config.set("gedcom_path", "No file selected")
            with open(path, 'wb') as file:
                pickle.dump(self.config.dict, file)

        path = self.config.get("gedcom_path")

    @staticmethod
    def fatal_error(msg):
        """ Fatal error -  Notify user and shutdown """
        messagebox.showerror("Error", msg)
        sys.exit()


r = ReviewWindow()
