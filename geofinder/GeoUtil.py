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
import collections
import os
import re

import phonetics


class Entry:
    NAME = 0
    ISO = 1
    ADM1 = 2
    ADM2 = 3
    LAT = 4
    LON = 5
    FEAT = 6
    ID = 7
    SDX = 8
    PREFIX = 8  # Note - item 8 is overloaded with Soundex in DB and Prefix for result
    SCORE = 9
    MAX = 9
    POP = 14


class Result:
    # Result codes for lookup
    STRONG_MATCH = 8
    MULTIPLE_MATCHES = 7
    PARTIAL_MATCH = 6
    WILDCARD_MATCH = 5
    SOUNDEX_MATCH = 4
    DELETE = 3
    NO_COUNTRY = 2
    NO_MATCH = 1
    NOT_SUPPORTED = 0


# Result types that are successful matches
successful_match = [Result.STRONG_MATCH, Result.PARTIAL_MATCH, Result.WILDCARD_MATCH, Result.SOUNDEX_MATCH, Result.MULTIPLE_MATCHES]

Query = collections.namedtuple('Query', 'where args result')

def lowercase_match_group(matchobj):
        return matchobj.group().lower()

def capwords(nm):
    # Change from lowercase to Title Case but fix the title() apostrophe bug
    if nm is not None:
        # Use title(), then fix the title() apostrophe defect
        nm = nm.title()

        # Fix handling for contractions not handled correctly by title()
        poss_regex = r"(?<=[a-z])[\']([A-Z])"
        nm = re.sub(poss_regex, lowercase_match_group, nm)

    return nm

def get_soundex(txt):
    res = phonetics.dmetaphone(txt)
    return res[0]

def get_directory_name() -> str:
    return "geoname_data"

def get_cache_directory(dirname):
    """ Return the directory for cache files """
    return os.path.join(dirname, "cache")


type_names = {
    "CH": 'Church',
    "CSTL": 'Castle',
    "CMTY": 'Cemetery',
    "EST": 'Estate',
    "HSP": 'Hospital',
    "HSTS": 'Historical',
    "ISL": 'Island',
    "MT": 'Mountain',
    "MUS": 'Museum',
    "PAL": 'Palace',
    "PRK": 'Park',
    "PRN": 'Prison',
    "RUIN": 'Ruin',
    "SQR": 'Square',
    "VAL": 'Valley',
    "ADM1": 'State',
    "ADM2": 'County',
    "ADM3": 'Township',
    "ADM4": 'Township',
    "PPL": 'City',
    "PPLA": 'City',
    "PPLA2": 'City',
    "PPLA3": 'City',
    "PPLA4": 'City',
    "PPLC": 'City',
    "PPLG": 'City',
    "PPLH": 'City',
    "PPLL": 'Village',
    "PPLQ": 'Historical',
    "PPLX": 'Neighborhood'
}
