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
import sys
from pathlib import Path

import Loc
from geodata import Geodata


class Example():
    """
    Example program for Geodata gazeteer.
    1. Create folder in home directory:  example/cache
    2. Download gb.txt from geonames.org and place in example/cache.  (Just Great Britain data so fast to test)
    3. Run example.py
    """
    def __init__(self):
        # Set up standard logging.  Change this to DEBUG for more detail
        logging.getLogger(__name__)
        fmt = "%(levelname)s %(name)s.%(funcName)s %(lineno)d: %(message)s"
        logging.basicConfig(level=logging.INFO, stream=sys.stdout, format=fmt)

        # Load geoname data. This will build geoname DB if not found
        directory = os.path.join(str(Path.home()), "example")
        self.geodata = Geodata.Geodata(directory_name=directory, progress_bar=None, enable_spell_checker=False,
                                       show_message=True, exit_on_error=True,
                                       languages_list_dct={'en'},
                                       feature_code_list_dct=features,
                                       supported_countries_dct={'fr', 'gb'})

        # Read in Geoname Gazeteer file - city names, lat/long, etc.
        error = self.geodata.open()
        if error:
            print(f"Missing geoname Files in {directory}: gb.txt or allcountries.txt from geonames.org")
            raise ValueError('Missing files from geonames.org')

    def lookup_place(self, entry):
        place: Loc.Loc = Loc.Loc()
        self.geodata.find_location(location=entry, place=place, plain_search=False)
        flags = self.geodata.sort_results(place)

        print(f'{len(place.georow_list)} matches for {entry}')

        if len(place.georow_list) > 0:
            self.geodata.process_results(place=place, flags=flags)
            place.set_place_type()

            name = f'{place.get_long_name(None)}'
            print(f'   Best: [{name}]  Prefix=[{place.prefix}{place.prefix_commas}] Score=')
        else:
            print('   NO MATCH')

# Geoname feature types to add to database.  Other feature types will be ignored
features = {"ADM1", "ADM2", "ADM3", "ADM4", "ADMF", "CH", "CSTL", "CMTY", "EST ", "HSP", "FT",
            "HSTS", "ISL", "MSQE", "MSTY", "MT", "MUS", "PAL", "PPL", "PPLA", "PPLA2", "PPLA3", "PPLA4",
            "PPLC", "PPLG", "PPLH", "PPLL", "PPLQ", "PPLX", "PRK", "PRN", "PRSH", "RUIN", "RLG", "STG", "SQR", "SYG", "VAL"}

if __name__ == "__main__":
    ex = Example()
    ex.lookup_place('eddinburg,,scotland')
    ex.lookup_place('d*,--feature=CSTL,--iso=GB')
    ex.lookup_place('12 main, westminster,england')
    ex.lookup_place('cant* cath*,england')
