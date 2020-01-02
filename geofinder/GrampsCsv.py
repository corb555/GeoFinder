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
import copy
import logging
import math
import re

from geodata import Loc
from geodata import Geodata


class CSVEntry:
    PLACE_ID = 0
    TITLE = 1
    NAME = 2
    LAT = 3
    LON = 4
    FEAT = 5
    ADMIN1_ID = 6
    ADMIN2_ID = 7
    ISO = 8
    ENCLOSED_BY = 9
    TYPE = 10


class GrampsCsv:
    """
    Create a CSV file which can be used to import place names into Gramps
    This will create any missing 'enclosure' locations, e.g. Dallas, Texas is enclosed by Texas
    First call add_place() for each place.
    When done adding places, call create_enclosures().  This will create any missing enclosure locations
    Then call write_csv_file().   This will write out a CSV file
    """

    def __init__(self, in_path: str, geodata: Geodata):
        """
        #Args:
            in_path: This will write to in_path with .CSV appended
            geodata: geodata.Geodata
        """
        self.logger = logging.getLogger(__name__)
        self.geodata = geodata

        # There is a separate dictionary for each hierarchy (prefix, city, adm2, adm1, country)
        self.hierarchy_dictionaries = [{}, {}, {}, {}, {}]

        self.csvfile = None

        if in_path is not None:
            csv_path = in_path + '.' + 'csv'
            self.csvfile = open(csv_path, "w", encoding='utf-8')
            self.logger.debug(f'CSV file {csv_path}')

    def write_asis(self, entry: str):
        """ Write entry as-is since it couldnt be found """
        pass

    def add_place(self, place: Loc.Loc):
        """
        Create a CSV node in Dictionary for specified place with the following:
          Place (ID), Title, Name, Type, latitude, longitude, enclosed_by
        Call create_csv_node for each place in the ancestry file
        #Args:
            place: Loc.Loc location
        """
        if place.original_entry == '':
            return

        csv_row = [''] * 11
        _set_CSV_place_type(place)

        if place.id == '':
            _set_CSV_place_type(place)
            place.id = self._get_hierarchy_key(place)

        place.set_place_type_text()

        csv_row[CSVEntry.PLACE_ID] = place.id
        csv_row[CSVEntry.ENCLOSED_BY] = place.enclosed_by
        csv_row[CSVEntry.TITLE] = place.prefix + place.prefix_commas + place.original_entry
        csv_row[CSVEntry.FEAT] = place.feature
        csv_row[CSVEntry.LAT] = f'{float(place.lat):.4f}'
        csv_row[CSVEntry.LON] = f'{float(place.lon):.4f}'
        csv_row[CSVEntry.ADMIN2_ID] = place.admin2_id
        csv_row[CSVEntry.ADMIN1_ID] = place.admin1_id
        csv_row[CSVEntry.ISO] = place.country_iso
        csv_row[CSVEntry.NAME] = _get_csv_name(place)
        csv_row[CSVEntry.TYPE] = place.result_type_text

        #  There is a separate dictionary for each entity tier (prefix, city, adm2, adm1, country)
        key = self._get_hierarchy_key(place)
        dict_idx = _get_dict_idx(place)

        if dict_idx == 0:
            # This node is at country level - so no enclosure
            place.enclosed_by = ''
            csv_row[CSVEntry.ENCLOSED_BY] = ''

        if place.enclosed_by != '':
            # Validate enclosure
            if hierarchy_level(key) <= hierarchy_level(csv_row[CSVEntry.ENCLOSED_BY]) and hierarchy_level(key) > 0:
                msg = f'Incorrect Enclosure for [{place.original_entry}]. Key= [{key}] Enclosure= [{csv_row[CSVEntry.ENCLOSED_BY]}]'
                self.logger.warning(msg)
            elif hierarchy_level(key) < hierarchy_level(csv_row[CSVEntry.ENCLOSED_BY]) and hierarchy_level(key) == 0:
                msg = f'Incorrect Enclosure for [{place.original_entry}]. Key= [{key}] Enclosure= [{csv_row[CSVEntry.ENCLOSED_BY]}]'
                self.logger.warning(msg)

        # See if this is a synthetic ID or Ancestry ID
        if '_' in place.id or len(place.id)<4:
            # Synthetic ID.  We created this place ID.  It has no ancestry events tied to it and is lower priority
            # than an Ancestry place ID (which has events).  Only add it if we don't already have an Ancestry Place ID
            res = self.hierarchy_dictionaries[dict_idx].get(key.upper())
            if res is None:
                # Nothing there, add this row
                self.hierarchy_dictionaries[dict_idx][key.upper()] = csv_row
            else:
                # An ancestry node is already there so use existing
                place.id = res[CSVEntry.PLACE_ID]
        else:
            # Place ID came from the Ancestry data and takes priority since it is already linked to
            # events.  Add this
            self.hierarchy_dictionaries[dict_idx][key.upper()] = csv_row

        # self.logger.debug(f'\nCREATE CSV NODE {key.upper()} idx={dict_idx}: {row}\n{place.formatted_name}')

    def create_enclosures(self):
        """
        Walk through all entries and create any missing enclosure items
        """
        self.logger.debug('\n\n******** DONE \n  CREATE CSV ENCLOSURES *********')
        place = Loc.Loc()

        # Create any missing enclosure records
        # There are separate dictionaries for each tier (prefix, city, county, country).
        # We need to go through prefix dict, then city dict, etc (starting at bottom tier)
        for idx, dictionary in reversed(list(enumerate(self.hierarchy_dictionaries))):
            self.logger.debug(f'===TABLE {idx}===')
            for key in dictionary:
                _retrieve_csv_place(self.hierarchy_dictionaries, self.geodata, place, key, idx)
                self.logger.debug(f'** CSV {key} {place.original_entry}')

                # Create enclosure for each node at this level
                self._create_enclosed_by(place)

    def write_csv_file(self):
        """
        Write out as CSV file for import to Gramps
        """
        if self.csvfile is not None:
            # Write CSV header
            self.csvfile.write('Place,Title,Name,Type,latitude,longitude,enclosed_by\n')
            self.logger.debug('*** OUTPUT TABLE ***')

            # For each dictionary, walk through all keys and output as CSV row
            for idx, dictionary in enumerate(self.hierarchy_dictionaries):
                for key in dictionary:
                    row = dictionary[key]
                    # self.logger.debug(f'IDX={idx} {key} : {row}')
                    self._output_row(row)

            self.csvfile.close()

    def _create_enclosed_by(self, place: Loc.Loc):
        """
        Create EnclosedBy elements in Dictionary for CSV file
        :return: None
        """
        self.logger.debug(f'\nCREATE ENCLOSURE FOR {place.original_entry}')
        enclosure_place: Loc.Loc = copy.copy(place)
        enclosure_place.id = ''

        # Move up to enclosure level
        success = self._move_up_level(enclosure_place=enclosure_place, idx=_get_dict_idx(enclosure_place))
        if success:
            place.enclosed_by = enclosure_place.id
            self._update_enclosure_id(place)
        return

    def _get_hierarchy_key(self, place):
        # Create key of format:  prefix_city_adm2ID_adm1ID_ISO    Any segments missing are left out.
        if place.admin2_id == '':
            self.logger.warning(f'{place.original_entry} admin2_id blank')
            self.geodata.geo_files.geodb.wide_search_admin2_id(place)
        if place.admin2_id == '' and len(place.admin2_name.strip(' ')) > 0:
            place.admin2_id = ' '
        if place.place_type == Loc.PlaceType.COUNTRY:
            key = f'{place.country_iso}'
        elif place.place_type == Loc.PlaceType.ADMIN1:
            key = f'{place.admin1_id}_{place.country_iso}'
        elif place.place_type == Loc.PlaceType.ADMIN2:
            key = f'{place.admin2_id}_{place.admin1_id}_{place.country_iso}'
        elif place.place_type == Loc.PlaceType.CITY:
            key = f'{place.city1.strip(" ")}_{place.admin2_id}_{place.admin1_id}_{place.country_iso}'
        elif place.place_type == Loc.PlaceType.PREFIX:
            key = f'{place.prefix.strip(" ")}_{place.city1.strip(" ")}_{place.admin2_id}_{place.admin1_id}_{place.country_iso}'
        else:
            msg = f'Get key - Unknown place type for {place.formatted_name}. Type={place.place_type}'
            raise Exception(msg)

        key = key.strip('_')
        key = key.strip('_')
        key = key.strip(' ')
        # self.logger.debug(f'key={key.upper().strip("_")} type={place.place_type}')
        return key.upper()

    def _move_up_level(self, enclosure_place, idx) -> bool:
        # Switch place type to next level higher
        enclosure_place.lat = 99.9
        enclosure_place.lon = 99.9

        if enclosure_place.place_type == Loc.PlaceType.COUNTRY:
            # Already at top
            enclosure_place.feature = 'ADM0'
            return False
        elif enclosure_place.place_type == Loc.PlaceType.ADMIN1:
            enclosure_place.feature = 'ADM1'
            enclosure_place.place_type = Loc.PlaceType.COUNTRY
        elif enclosure_place.place_type == Loc.PlaceType.ADMIN2:
            enclosure_place.feature = 'ADM2'
            enclosure_place.place_type = Loc.PlaceType.ADMIN1
        elif enclosure_place.place_type == Loc.PlaceType.CITY:
            enclosure_place.place_type = Loc.PlaceType.ADMIN2
        elif enclosure_place.place_type == Loc.PlaceType.PREFIX:
            enclosure_place.place_type = Loc.PlaceType.CITY
        else:
            msg = f'Move Up - Unknown place type for {enclosure_place.formatted_name}. Type={enclosure_place.place_type}'
            raise Exception(msg)

        enclosure_place.remove_old_fields()
        enclosure_place.formatted_name = enclosure_place.get_long_name(None)
        enclosure_place.set_place_type_text()
        # enclosure_place.city1 = tkns[1]
        save_type = enclosure_place.place_type
        self.geodata.find_best_match(enclosure_place.formatted_name, enclosure_place)
        enclosure_place.place_type = save_type
        enclosure_place.remove_old_fields()
        enclosure_place.formatted_name = enclosure_place.get_long_name(None)
        enclosure_place.set_place_type_text()
        enclosure_place.id = self._get_hierarchy_key(enclosure_place)

        # place.formatted_name = place.format_full_nm(None)
        self.logger.debug(f'\nMOVED UP TO {enclosure_place.formatted_name}')

        self.add_place(enclosure_place)

        new_idx = _get_dict_idx(enclosure_place)
        if new_idx < idx:
            # Successfully moved up in hierarchy
            return True
        else:
            msg = f'Move Up - Index error {enclosure_place.formatted_name}. Type={enclosure_place.place_type} idx={idx} new_idx={new_idx}'
            raise Exception(msg)

    def _update_enclosure_id(self, place):
        key = self._get_hierarchy_key(place)
        dict_idx = _get_dict_idx(place)
        row = self.hierarchy_dictionaries[dict_idx].get(key.upper())
        if row:
            if not re.match(r'P\d\d\d\d', row[CSVEntry.ENCLOSED_BY]):
                row[CSVEntry.ENCLOSED_BY] = place.enclosed_by
                self.hierarchy_dictionaries[dict_idx][key.upper()] = row
                self.logger.debug(f'UPDATE ENC for {dict_idx}:{key} New Enclosure=[{place.enclosed_by}]')
            else:
                pass
        else:
            self.logger.warning(f'@@@@@@@@ Cant find row {key}')

    def _output_row(self, row):
        if len(row[CSVEntry.ENCLOSED_BY]) > 0:
            enc = f'[{row[CSVEntry.ENCLOSED_BY]}]'
        else:
            enc = ''
        if self.csvfile is not None:
            # 0Place (ID), 1Title, 2Name, 3Type, 4latitude, 5longitude, 6enclosed_by
            title = capwords(row[CSVEntry.TITLE])
            name = capwords(row[CSVEntry.NAME])

            if math.isnan(float(row[CSVEntry.LAT])) or math.isnan(float(row[CSVEntry.LAT])):
                self.csvfile.write(f'[{row[CSVEntry.PLACE_ID]}],"{title}","{name}",{row[CSVEntry.TYPE]},'
                                   f' , ,{enc},\n')
            else:
                self.csvfile.write(f'[{row[CSVEntry.PLACE_ID]}],"{title}","{name}",{row[CSVEntry.TYPE]},'
                                   f'{row[CSVEntry.LAT]},{row[CSVEntry.LON]},{enc},\n')


def _set_CSV_place_type(place: Loc.Loc):
    place.set_place_type()
    if len(place.prefix) > 0:
        place.place_type = Loc.PlaceType.PREFIX


def _get_csv_name(place):
    if place.place_type == Loc.PlaceType.COUNTRY:
        place.formatted_name = place.country_name
        nm = place.country_name
    elif place.place_type == Loc.PlaceType.ADMIN1:
        nm = place.admin1_name
    elif place.place_type == Loc.PlaceType.ADMIN2:
        nm = place.admin2_name
    elif place.place_type == Loc.PlaceType.CITY:
        nm = place.city1
    elif place.place_type == Loc.PlaceType.PREFIX:
        nm = place.prefix
    else:
        msg = f'Get name - Unknown place type for {place.formatted_name}. Type={place.place_type}'
        raise Exception(msg)
    return nm


def _retrieve_csv_place(hierarchy_dictionaries, geodata, place: Loc.Loc, key, idx):
    """
    Lookup key in dictionary and fill in place with data from dictionary entry
    #Args:
        hierarchy_dictionaries:
        geodata:
        place:
        key:
        idx:

    #Returns:
        Fills in place with data from dictionary entry
    """
    # 0Place (ID), 1Title, 2Name, 3Type, 4latitude, 5longitude, 6enclosed_by
    row = hierarchy_dictionaries[idx].get(key)
    key_tokens = key.split("_")
    place.place_type = len(key_tokens) - 1
    # self.logger.debug(f'{row}')
    place.feature = row[CSVEntry.FEAT]

    place.original_entry = row[CSVEntry.TITLE]
    place.country_iso = row[CSVEntry.ISO]
    place.country_name = geodata.geo_files.geodb.get_country_name(place.country_iso)
    place.enclosed_by = row[CSVEntry.ENCLOSED_BY]

    place.lat: float = float(row[CSVEntry.LAT])
    place.lon: float = float(row[CSVEntry.LON])

    place.admin2_id = row[CSVEntry.ADMIN2_ID]
    place.admin1_id = row[CSVEntry.ADMIN1_ID]
    place.admin1_name = str(geodata.geo_files.geodb.get_admin1_name(place))
    place.admin2_name = str(geodata.geo_files.geodb.get_admin2_name(place))
    if place.admin2_name is None:
        place.admin2_name = ''
    if place.admin1_name is None:
        place.admin1_name = ''

    tokens = place.original_entry.split(',')
    if len(tokens) > 3:
        place.city1 = tokens[-4]
    if len(tokens) > 4:
        place.prefix = tokens[-5]

    place.id = row[CSVEntry.PLACE_ID]


def hierarchy_level(key):
    # Each hierarchy adds an '_' to the key.  Our underscore count must be less than enclosure underscore count
    return key.count('_')


def _get_dict_idx(place):
    # Get the dictionary index for this place type
    return place.place_type


def _lowercase_match_group(matchobj):
    return matchobj.group().lower()


def capwords(text):
    """
    Change text from lowercase to Title Case (but fix the title() apostrophe bug)
    #Args:
        text:
    #Returns:
        Text with Title Case
    """
    if text is not None:
        # Use title(), then fix the title() apostrophe defect where letter after apostrophe is made caps
        text = text.title()

        # Fix handling for contractions not handled correctly by title()
        poss_regex = r"(?<=[a-z])[\']([A-Z])"
        text = re.sub(poss_regex, _lowercase_match_group, text)

    return text
