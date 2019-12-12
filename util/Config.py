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

from tkinter import messagebox

import tk_helper

from geodata import GeoUtil
from util import CachedDictionary


class Config:
    """ Read and set configuration parameters """
    def __init__(self, directory):
        self.logger = logging.getLogger(__name__)
        self.config_cd: CachedDictionary
        self.config_cd = None

        self.directory: str = directory
        self.cache_dir = GeoUtil.get_cache_directory(self.directory)

    def get(self, param) -> str:
        res = self.config_cd.dict.get(param)
        if res is None:
            res = ''
        return res

    def set(self, name: str, val: str):
        self.config_cd.dict[name] = val

    def write(self):
        if self.config_cd:
            self.config_cd.write()

    def read(self):
        fname = 'config.pkl'

        """ Read config file  """
        self.logger.debug(f'config read {self.cache_dir} {fname}')
        # Verify main directory exists
        if not os.path.exists(self.cache_dir):
            self.logger.warning(f"{self.cache_dir} folder not found.")
            tk_helper.fatal_error(f"{self.cache_dir} folder not found.  Please use Config button to correct")

        self.config_cd = CachedDictionary.CachedDictionary(self.cache_dir, fname)
        self.config_cd.read()

        if self.config_cd.error:
            self.logger.error(f'Config {os.path.join(self.cache_dir, fname)} not found')

            # Create empty config file
            path = os.path.join(self.cache_dir, "config.pkl")
            self.set("gedcom_path", "GEDCOM filename: <empty>")
            with open(path, 'wb') as file:
                pickle.dump(self.config_cd.dict, file)
            return True
        else:
            return False

    def valid_directories(self)->bool:
        if not os.path.exists(self.cache_dir):
            messagebox.showwarning('Folder Missing',f'Folder not found:\n\n{self.cache_dir}')
            return False
        else:
            return True

    def create_directories(self)->bool:
        if not os.path.exists(self.cache_dir):
            self.logger.info(f'Creating folder {self.cache_dir}')
            try:
                os.makedirs(self.cache_dir)
                if os.path.exists(self.cache_dir):
                    self.logger.info(f'Created cache folder {self.cache_dir}')
                else:
                    messagebox.showerror('Geoname Data Folders not created',
                                         f'Error \n\n{self.cache_dir} ')
                    return True
            except OSError as e:
                self.logger.warning(e)
                messagebox.showerror('Geoname Data Folders not created',
                                       f'Error {e}\n\n{self.cache_dir} ')
                return True

        return False



