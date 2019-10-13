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
import os
import tkinter as tk
from typing import Dict

from geofinder import UtilListboxFrame, GeoDB, Loc
from geofinder.CachedDictionary import CachedDictionary

GEOID_TOKEN = 1
PREFIX_TOKEN = 2


class SetupReplaceFrame(UtilListboxFrame.ListboxFrame):
    """
    SetupReplaceFrame is derived from ListboxFrame
    Display items in Global Replace List

    ListboxFrame Displays a scrolling list box that is based on a CachedDictionary.
    ListboxFrame defines the overall Grid Layout
    """

    def __init__(self, frame, title: str, dir_name: str, cache_filename: str):
        # Initialize GEO database
        self.geodb = GeoDB.GeoDB(os.path.join(dir_name, 'geodata.db'))

        # Read in dictionary listing output text replacements
        self.output_replace_cd = CachedDictionary(dir_name, "output_list.pkl")
        self.output_replace_cd.read()
        self.output_replace_dct: Dict[str, str] = self.output_replace_cd.dict

        super().__init__(frame, title, dir_name, cache_filename)
        self.tree.heading("#0", text="Original", anchor=tk.W)
        self.tree.heading("pre", text="Replacement", anchor=tk.W)

    def load_handler(self):
        # Load in list and display
        self.clear_display_list(self.tree)
        place = Loc.Loc()

        for item in sorted(self.dict):
            # get lat long
            replacement = self.dict[item]
            rep_token = replacement.split('@')
            if len(rep_token) < 2:
                self.logger.debug(f'blank item=[{item}] rep=[{replacement}]')
                continue
            place.target = rep_token[GEOID_TOKEN]
            self.geodb.lookup_geoid(place=place)

            if len(place.georow_list) > 0:
                # Copy geo row to Place
                self.geodb.copy_georow_to_place(row=place.georow_list[0], place=place)
                if 'oston' in item:
                    self.logger.debug(f'{item} id={rep_token[GEOID_TOKEN]} state={place.admin1_id}')
            else:
                if len(place.target) == 0:
                    place.clear()
                    place.city1 = f'<DELETE>'
                else:
                    place.clear()
                    place.city1 = f'Database error for {replacement}'
                place.place_type = Loc.PlaceType.CITY

            # Get prefix if there was one
            if len(rep_token) > 2:
                place.prefix = rep_token[PREFIX_TOKEN]

            nm = place.format_full_nm(self.output_replace_dct)
            if len(place.prefix) > 0:
                line = f'[{place.prefix}]{place.prefix_commas}{nm}'
            else:
                line = f'{nm}'

            self.list_insert(self.tree, item, line)
