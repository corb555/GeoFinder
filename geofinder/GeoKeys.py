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
import unidecode


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
    MAX = 9


class Result:
    # Result codes for lookup
    EXACT_MATCH = 0
    MULTIPLE_MATCHES = 2
    NO_MATCH = 3
    NOT_SUPPORTED = 4
    NO_COUNTRY = 5
    PARTIAL_MATCH = 6
    DELETE = 7


# Result types that are successful matches
successful_match = [Result.EXACT_MATCH, Result.PARTIAL_MATCH]

Query = collections.namedtuple('Query', 'where args result')


def get_soundex(txt):
    res = phonetics.dmetaphone(txt)
    return res[0]


def get_directory_name() -> str:
    return "geoname_data"


def get_cache_directory(dirname):
    """ Return the directory for cache files """
    return os.path.join(dirname, "cache")


def _phrase_normalize(name) -> str:
    """ Strip spaces and normalize spelling for items such as Saint and County """
    # Replacement patterns to clean up entries
    res = re.sub('saint |st. ', 'st ', name)  # Normalize Saint
    res = re.sub(r' co\.', ' county', res)  # Normalize County
    res = re.sub('  +', ' ', res)  # Strip multiple space
    res = re.sub('county of ([^,]+)', r'\g<1> county', res)  # Normalize 'Township of X' to 'X Township'
    res = re.sub('township of ([^,]+)', r'\g<1> township', res)  # Normalize 'Township of X' to 'X Township'
    res = re.sub('cathedral of ([^,]+)', r'\g<1> cathedral', res)  # Normalize 'Township of X' to 'X Township'
    return res

def normalize(res) -> str:
    """ Strip commas. Also strip spaces and normalize spelling for items such as Saint and County and chars   ø ß """

    # Convert UT8 to ascii
    res = unidecode.unidecode(res)

    # remove all punctuation
    res = str(res).lower()
    res = re.sub(r"[^a-zA-Z0-9 $.*']+", " ", res)
    res = _phrase_normalize(res)
    return res.strip(' ')


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
