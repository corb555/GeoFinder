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
import configparser
import os
import sys
from pathlib import Path
from tkinter import messagebox, filedialog

from geofinder import GeoKeys


class IniHandler:
    def __init__(self, home_path:str, ini_name):
        self.directory:Path = Path()
        #self.home_path = str(Path.home())
        self.home_path:Path = Path(home_path)

        self.ini = configparser.ConfigParser()
        self.ini_path:Path = Path(os.path.join(str(self.home_path), ini_name))

    def ini_read(self, section, key):
        # read item from ini file
        val = None
        try:
            self.ini.read(self.ini_path)
            val = self.ini.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, configparser.MissingSectionHeaderError) as e:
            print ('no section')

        # read value from a section
        return val

    def ini_set(self, section, key: str, val: str):
        # update existing value
        self.ini.set(section, key, val)
        # save to a file
        with open(str(self.ini_path), 'w') as configfile:
            self.ini.write(configfile)

    def ini_add_section(self, section):
        # add a new section and some values
        try:
            self.ini.add_section(section)
        except configparser.DuplicateSectionError:
            print('Duplicate section')

        # save to a file
        with open(str(self.ini_path), 'w') as configfile:
            self.ini.write(configfile)

    def get_directory_from_ini(self) -> str:
        if self.ini_path.is_file():
            val = self.ini_read('PATH', 'DIRECTORY')
            if val:
                self.directory = val
            else:
                # Not Found.  Create INI file
                self.directory = Path(os.path.join(str(self.home_path), GeoKeys.get_directory_name()))
                self.ini_add_section('PATH')
                self.ini_set(section='PATH', key='DIRECTORY', val=str(self.directory))
        else:
            # Not Found.  Create INI file
            self.directory = Path(os.path.join(str(self.home_path), GeoKeys.get_directory_name()))
            self.ini_add_section('PATH')
            self.ini_set(section='PATH', key='DIRECTORY', val=str(self.directory))

        #  if directory doesnt exist, prompt user for folder
        if not Path(self.directory).is_dir():
            messagebox.showinfo('Geofinder Folder not found', 'Choose Folder for GeoFinder data in next dialog')
            self.directory = filedialog.askdirectory(initialdir=self.home_path, title="Choose Folder for GeoFinder data")
            if len(self.directory) == 0:
                sys.exit()
            else:
                self.ini_add_section('PATH')
                self.ini_set(section='PATH', key='DIRECTORY', val=str(self.directory))
        return self.directory
