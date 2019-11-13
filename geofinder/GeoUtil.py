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
from difflib import SequenceMatcher

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

def _remove_matching_seq(text1: str, text2: str, attempts: int) -> (str, str):
    """
    Find largest matching sequence.  Remove it in text1 and text2.
            Private - called by remove_matching_sequences which provides a wrapper
    Call recursively until attempts hits zero or there are no matches longer than 1 char
    :param text1:
    :param text2:
    :param attempts: Number of times to remove largest text sequence
    :return:
    """
    s = SequenceMatcher(None, text1, text2)
    match = s.find_longest_match(0, len(text1), 0, len(text2))
    if match.size > 2:
        # Remove matched sequence from inp and out
        item = text1[match.a:match.a + match.size]
        text2 = re.sub(item, '', text2, count=1)
        text1 = re.sub(item, '', text1, count=1)
        if attempts > 0:
            # Call recursively to get next largest match and remove it
            text1, text2 = _remove_matching_seq(text1, text2, attempts - 1)
    return text1, text2

def remove_matching_sequences(text1: str, text2: str) -> (str, str):
    """
    Find largest sequences that match between text1 and 2.  Remove them from text1 and text2.
    :param text1:
    :param text2:
    :return:
    """
    # Prepare strings for input to remove_matching_seq
    # Swap all commas in text1 string to '@'.  This way they will never match comma in text2 string
    # Ensures we don;t remove commas and don't match across tokens
    text2 = re.sub(',', '@', text2)
    text1, text2 = _remove_matching_seq(text1=text1, text2=text2, attempts=15)
    # Restore commas in inp
    text2 = re.sub('@', ',', text2)
    return text1.strip(' '), text2.strip(' ')


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
