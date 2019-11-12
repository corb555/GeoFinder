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
from pathlib import Path
from tkinter import *

from geofinder import CachedDictionary,  GeoUtil, UtilLayout

try:
    import unidecode
except ModuleNotFoundError:
    print('Unidecode missing.')


class UtilMain:
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
        self.logger.info('Configuration')

        self.directory: str = os.path.join(str(Path.home()), GeoUtil.get_directory_name())
        self.cache_dir = GeoUtil.get_cache_directory()

        # Get configuration settings stored in config pickle file
        self.cfg: CachedDictionary.CachedDictionary = CachedDictionary.CachedDictionary(self.cache_dir, "config.pkl")

        if not os.path.exists(self.directory):
            self.logger.info(f'Creating main folder {self.directory}')
            os.makedirs(self.directory)

        if not os.path.exists(self.cache_dir):
            self.logger.info(f'Creating cache folder {self.cache_dir}')
            os.makedirs(self.cache_dir)

        self.cfg.read()

        # Verify config -  test to see if gedcom file accessible
        self.get_config()

        # Create App window
        self.root = Tk()
        self.root["padx"] = 30
        self.root["pady"] = 30
        self.root.title('GeoUtil')

        UtilLayout.UtilLayout(root=self.root, directory=self.directory, cache_dir=self.cache_dir)

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

            self.cfg.set("gedcom_path", "No file selected")
            with open(path, 'wb') as file:
                pickle.dump(self.cfg.dict, file)

        path = self.cfg.get("gedcom_path")

