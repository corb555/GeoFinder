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

from geofinder import CachedDictionary
from geofinder.Widge import Widge


class Config:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_cd: CachedDictionary
        self.config_cd = None

    def get(self, param)->str:
        res = self.config_cd.dict.get(param)
        if res is None:
            res = ''
        return res

    def set(self, name:str, val:str):
        self.config_cd.dict[name] = val

    def write(self):
        self.config_cd.write()

    def read(self, directory, fname:str):
        """ Read config file  """
        self.logger.debug(f'config read {directory} {fname}')
        # Verify main directory exists
        if not os.path.exists(directory):
            self.logger.warning(f"{directory} folder not found.")
            Widge.fatal_error(f"{directory} folder not found.  Please run GeoUtil.py to correct")

        self.config_cd = CachedDictionary.CachedDictionary(directory, fname)
        self.config_cd.read()

        if self.config_cd.error:
            self.logger.error(f'Config {os.path.join(directory, fname)} not found')

            # Create empty config file
            path = os.path.join(directory, "config.pkl")
            self.set("gedcom_path", "GEDCOM filename: <empty>")
            with open(path, 'wb') as file:
                pickle.dump(self.config_cd.dict, file)
            return True
        else:
            return False
