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
from typing import Dict


class CachedDictionary:
    """ Use a Python Pickle file to maintain a cached dictionary """

    def __init__(self, cache_directory, fname):
        self.logger = logging.getLogger(__name__)
        self.cache_directory = cache_directory
        self.fname = fname
        self.dict: Dict[str, str] = {}
        self.error = False

    def get(self, val):
        return self.dict.get(val)

    def set(self, key, val):
        self.dict[key] = val

    def read(self):
        # Load Pickle file into dictionary

        if self.cache_directory is None:
            self.logger.debug(f'No directory specified for {self.fname}')
            return True
        path = os.path.join(self.cache_directory, self.fname)
        if os.path.exists(path):
            with open(path, 'rb') as file:
                self.dict = pickle.load(file)
                self.logger.debug(f'Read success CachedDict dir={self.cache_directory} fname={self.fname} len={len(self.dict)}')
                self.error = False
                return False
        else:
            self.logger.error("Missing {}".format(path))
            # Create empty file
            try:
                with open(path, 'wb') as file:
                    pickle.dump(self.dict, file)
            except OSError as e:
                messagebox.showwarning('File Error',f'{e}')
            self.error = True
            return True

    def write(self):
        # Write dictionary to Pickle file
        if self.cache_directory is None:
            return True
        path = os.path.join(self.cache_directory, self.fname)
        self.logger.debug("Write {}".format(path))

        try:
            with open(path, 'wb') as file:
                pickle.dump(self.dict, file)
        except OSError as e:
            messagebox.showwarning('File Write Error',e)
            return  True

        return False
