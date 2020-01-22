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
import re
import tkinter as tk
from tkinter import ttk
from typing import Dict, Match

from geodata import Loc, GeoDB
from tk_helper import TKHelper as TkHelp

import ReplacementDictionary
from geofinder.util import GridPosition, CachedDictionary
from util_menu import UtilListboxFrame


class SetupReplaceFrame(UtilListboxFrame.ListboxFrame):
    """
    Display Global Replace List.  User can delete items or edit prefix for an item
    Derived from ListboxFrame which displays a scrolling list box that is based on a CachedDictionary.   
    ListboxFrame defines the overall Grid Layout   
    """

    def __init__(self, frame, title: str, dir_name: str, cache_filename: str):
        # Initialize GEO database
        self.geodb = GeoDB.GeoDB(db_path=os.path.join(dir_name, 'geodata.db'),
                                 spellcheck=None, show_message=True, exit_on_error=True, set_speed_pragmas=True,
                                 db_limit=150)

        # Read in dictionary listing output text replacements
        self.output_replace_cd = CachedDictionary.CachedDictionary(dir_name, "output_list.pkl")
        self.output_replace_cd.read()
        self.output_replace_dct: Dict[str, str] = self.output_replace_cd.dict

        # Add these widgets in addition to the standard widgets we inherit from ListBoxFrame
        self.update_button = ttk.Button(frame, text="update", command=self.update_handler, width=UtilListboxFrame.BUTTON_WIDTH)
        self.update_label = TkHelp.CLabel(frame, text="Edit prefix below and click Update", style='Info.TLabel')
        self.edit_entry: TkHelp.CEntry = TkHelp.CEntry(frame, text="   ", width=55)  # , style='Info.TLabel')

        super().__init__(frame, title, dir_name, cache_filename)
        self.tree.heading("#0", text="Original", anchor=tk.W)
        self.tree.heading("pre", text="Replacement", anchor=tk.W)
        self.status.text = "Click to select items above. Then click Remove to remove item, or edit prefix below."
        self.key = ''
        self.val = ''
        self.item = None

    def load_handler(self):
        # Load in global replace list and display
        self.clear_display_list(self.tree)
        place = Loc.Loc()
        self.edit_entry.text = "Loading Replacement Dictionary"

        for key in sorted(self.dict):
            # Key is the original name.  Value is @GEOID@PREFIX
            # replacement = self.dict[key]
            prefix, geoid = ReplacementDictionary.parse_replacement_entry(self.dict[key])
            if geoid == '':
                self.logger.warning(f'blank item=[{key}] ')
                continue
            place.target = geoid
            # Lookup GEOID to get location info
            self.geodb.get_geoid(place=place)

            if len(place.georow_list) > 0:
                # Found it.  Copy geo row to Place
                self.geodb.copy_georow_to_place(row=place.georow_list[0], place=place)
            else:
                if len(place.target) == 0:
                    place.clear()
                    place.city1 = f'<DELETE>'
                else:
                    place.clear()
                    place.city1 = f'Database error for GeoID {geoid}'
                place.place_type = Loc.PlaceType.CITY

            # Get prefix if there was one
            place.prefix = prefix

            place.set_place_type()
            nm = place.get_long_name(self.output_replace_dct)
            if len(place.prefix) > 0:
                line = f'[{place.prefix}]{place.prefix_commas}{nm}'
            else:
                line = f'{nm}'

            self.list_append(self.tree, key, line)

        self.edit_entry.text = ""

    def configure_widgets(self, frm):
        # Add the standard widgets in ListBoxFrame
        super().configure_widgets(frm)

        # Add these in addition to the standard widgets in ListBoxFrame
        # todo - remove set_grid_position and just use element.grid()
        GridPosition.set_grid_position(self.update_button, "entry_button", grd=self.grd)
        GridPosition.set_grid_position(self.update_label, "entry_label", grd=self.grd)
        GridPosition.set_grid_position(self.edit_entry, "country_entry", grd=self.grd)
        self.tree.bind("<<TreeviewSelect>>", self.entry_focus_event_handler)

    def close(self):
        self.geodb.close()

    def update_handler(self):
        """ User clicked Update button.  Get prefix from edit widget, update list and dictionary with new prefix """
        if self.item is None:
            # User has not selected an item
            return
        
        new_prefix = self.edit_entry.text

        # Update Display list
        if len(new_prefix) > 0:
            line = f'[{new_prefix}],{self.val}'
        else:
            line = f'{self.val}'

        self.list_update(self.tree, self.key, line, self.item)

        # Update dictionary
        # Retrieve current dictionary item, update prefix and write it back
        pref, geoid = ReplacementDictionary.parse_replacement_entry(self.dict[self.key])
        self.dict[self.key] = ReplacementDictionary.build_replacement_entry(geoid, new_prefix)
        self.dirty_flag = True
        self.logger.debug(f'Update dict:{self.key} line:{ReplacementDictionary.build_replacement_entry(geoid, new_prefix)}')

    def entry_focus_event_handler(self, _):
        # User clicked item in list display.  Retrieve it and update entry field with the locations prefix
        # Save value and key so when user clicks update button we know which item we were on
        # Note - second param _ is to prevent warning for Event param which isn't used
        selitems = self.tree.selection()
        self.item = selitems[0]

        prefix = ''
        self.val = ''
        self.key = ''

        if selitems:
            self.key = self.tree.item(selitems[0], "text")  # get value in col #0
            rep = self.tree.item(selitems[0], "values")[0]  # get value in col #0

            # Pull out prefix.  Format is [prefix],location
            matches: Match = re.match(r'\[(?P<prefix>.+)\](?P<value>.+)', rep)

            if matches is not None:
                prefix = matches.group('prefix')
                self.val = matches.group('value').strip(',')
                self.val = self.val.strip(' ')
            else:
                self.val = rep

            self.edit_entry.text = prefix
            self.logger.debug(f"Clicked [{self.key}] pre=[{prefix}] val=[{self.val}]")
