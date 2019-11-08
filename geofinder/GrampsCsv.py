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

from geofinder import Loc, GeoKeys


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
    def __init__(self, in_path: str, geodata):
        self.logger = logging.getLogger(__name__)
        self.csv_path = in_path + '.' + 'csv'

        self.admin_table = [{}, {}, {}, {}, {}]
        self.csvfile = None
        self.geodata = geodata

    @staticmethod
    def get_dict_id(place):
        if place.place_type == Loc.PlaceType.COUNTRY:
            dict_idx = 0
        elif place.place_type == Loc.PlaceType.ADMIN1:
            dict_idx = 1
        elif place.place_type == Loc.PlaceType.ADMIN2:
            dict_idx = 2
        elif place.place_type == Loc.PlaceType.CITY:
            dict_idx = 3
        elif place.place_type == Loc.PlaceType.PREFIX:
            dict_idx = 4
        else:
            msg = f'Dictionary ID - Unknown place type for {place.name}. Type={place.place_type}'
            raise Exception(msg)
        return dict_idx

    def write_asis(self, entry:str):
        pass

    def get_csv_key(self, place):
        # Fill in admin2
        if place.admin2_id == '':
            self.geodata.geo_files.geodb.get_admin2_id(place)
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
            msg = f'Get key - Unknown place type for {place.name}. Type={place.place_type}'
            raise Exception(msg)

        key = key.strip('_')
        key = key.strip('_')
        key = key.strip(' ')
        # self.logger.debug(f'key={key.upper().strip("_")} type={place.place_type}')
        return key.upper()

    @staticmethod
    def set_CSV_place_type(place: Loc.Loc):
        place.set_place_type()
        if len(place.prefix) > 0:
            place.place_type = Loc.PlaceType.PREFIX

    @staticmethod
    def get_csv_name(place):
        if place.place_type == Loc.PlaceType.COUNTRY:
            place.name = place.country_name
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
            msg = f'Get name - Unknown place type for {place.name}. Type={place.place_type}'
            raise Exception(msg)
        return nm

    def create_csv_node(self, place: Loc.Loc):
        """
        Create CSV row in Dictionary:  Place (ID), Title, Name, Type, latitude, longitude,enclosed_by
        :param place:
        :return: None
        """
        if place.original_entry == '':
            return

        row = [''] * 11
        self.set_CSV_place_type(place)

        if place.id == '':
            self.set_CSV_place_type(place)
            place.id = self.get_csv_key(place)

        row[CSVEntry.PLACE_ID] = place.id
        row[CSVEntry.ENCLOSED_BY] = place.enclosed_by
        place.id = row[CSVEntry.PLACE_ID]

        row[CSVEntry.TITLE] = place.prefix + place.prefix_commas + place.original_entry
        row[CSVEntry.FEAT] = place.feature
        row[CSVEntry.LAT] = f'{float(place.lat):.4f}'

        row[CSVEntry.LAT] = f'{float(place.lat):.4f}'
        row[CSVEntry.LON] = f'{float(place.lon):.4f}'
        row[CSVEntry.ADMIN2_ID] = place.admin2_id
        row[CSVEntry.ADMIN1_ID] = place.admin1_id
        row[CSVEntry.ISO] = place.country_iso

        place.set_place_type_text()
        row[CSVEntry.NAME] = self.get_csv_name(place)
        row[CSVEntry.TYPE] = place.result_type_text
        key = self.get_csv_key(place)
        dict_idx = self.get_dict_id(place)

        if dict_idx == 0:
            place.enclosed_by = ''
            row[CSVEntry.ENCLOSED_BY] = ''

        if place.enclosed_by != '':
            if key.count('_') <= row[CSVEntry.ENCLOSED_BY].count('_') and key.count('_') > 0:
                msg = f'Incorrect Enclosure for [{place.original_entry}]. Key= [{key}] Enclosure= [{row[CSVEntry.ENCLOSED_BY]}]'
                self.logger.warning(msg)
            elif key.count('_') < row[CSVEntry.ENCLOSED_BY].count('_') and key.count('_') == 0:
                msg = f'Incorrect Enclosure for [{place.original_entry}]. Key= [{key}] Enclosure= [{row[CSVEntry.ENCLOSED_BY]}]'
                self.logger.warning(msg)

        if re.match(r'P\d\d\d\d', place.id):
            # our item has an ID with P9999,  add this row
            self.admin_table[dict_idx][key.upper()] = row
        else:
            res = self.admin_table[dict_idx].get(key.upper())
            if res is None:
                # Nothing there, add this row
                self.admin_table[dict_idx][key.upper()] = row
            else:
                # A node is already there and we don't have a P, so do nothing
                place.id = res[CSVEntry.PLACE_ID]

        #self.logger.debug(f'\nCREATE CSV NODE {key.upper()} idx={dict_idx}: {row}\n{place.name}')

    def move_up_level(self, enclosure_place, idx) -> bool:
        enclosure_place.lat = 99.9
        enclosure_place.lon = 99.9

        # Switch place type to next level higher
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
            msg = f'Move Up - Unknown place type for {enclosure_place.name}. Type={enclosure_place.place_type}'
            raise Exception(msg)

        enclosure_place.remove_old_fields()
        enclosure_place.name = enclosure_place.format_full_nm(None)
        enclosure_place.set_place_type_text()
        # enclosure_place.city1 = tkns[1]
        save_type = enclosure_place.place_type
        self.geodata.find_first_match(enclosure_place.name, enclosure_place)
        enclosure_place.place_type = save_type
        enclosure_place.remove_old_fields()
        enclosure_place.name = enclosure_place.format_full_nm(None)
        enclosure_place.set_place_type_text()
        enclosure_place.id = self.get_csv_key(enclosure_place)

        # place.name = place.format_full_nm(None)
        self.logger.debug(f'\nMOVED UP TO {enclosure_place.name}')

        self.create_csv_node(enclosure_place)

        new_idx = self.get_dict_id(enclosure_place)
        if new_idx < idx:
            return True
        else:
            msg = f'Move Up - Index error {enclosure_place.name}. Type={enclosure_place.place_type} idx={idx} new_idx={new_idx}'
            raise Exception(msg)

    def create_enclosed_by(self, place: Loc.Loc):
        """
        Create EnclosedBy elements in Dictionary for CSV file
        :return: None
        """
        self.logger.debug(f'\nCREATE ENCLOSURE FOR {place.original_entry}')
        enclosure_place = copy.copy(place)
        enclosure_place.id = ''

        # Move up to enclosure level
        success = self.move_up_level(enclosure_place, idx=self.get_dict_id(enclosure_place))
        if success:
            place.enclosed_by = enclosure_place.id
            self.update_enclosure_id(place)
        return

    def update_enclosure_id(self, place):
        key = self.get_csv_key(place)
        dict_idx = self.get_dict_id(place)
        row = self.admin_table[dict_idx].get(key.upper())
        if row:
            if not re.match(r'P\d\d\d\d', row[CSVEntry.ENCLOSED_BY]):
                row[CSVEntry.ENCLOSED_BY] = place.enclosed_by
                self.admin_table[dict_idx][key.upper()] = row
                self.logger.debug(f'UPDATE ENC for {dict_idx}:{key} New Enclosure=[{place.enclosed_by}]')
            else:
                pass
        else:
            self.logger.warning(f'@@@@@@@@ Cant find row {key}')

    def complete_csv(self):
        # Add location enclosures.  Create if not there already.  Then add as reference.
        self.logger.debug('\n\n******** DONE - CREATE CSV ENCLOSURES *********')
        place = Loc.Loc()

        # There are separate dictionaries for each hierarchy (prefix, city, county, country).
        # We need to go through prefix table, then city, etc (e.g. reversed order)
        # Create Enclosure records
        for idx, tbl in reversed(list(enumerate(self.admin_table))):
            self.logger.debug(f'===TABLE {idx}===')
            for key in tbl:
                self.retrieve_csv_place(self.admin_table, self.geodata, place, key, idx)
                self.logger.debug(f'** CSV {key} {place.original_entry}')

                # Create enclosure for each node at this level
                self.create_enclosed_by(place)

        if self.csv_path is not None:
            self.csvfile = open(self.csv_path, "w", encoding='utf-8')
            self.logger.debug(f'CSV file {self.csv_path}')
            self.csvfile.write('Place,Title,Name,Type,latitude,longitude,enclosed_by\n')

        # List CSV
        self.logger.debug('*** OUTPUT TABLE ***')
        for idx, tbl in enumerate(self.admin_table):
            for key in tbl:
                # TODO
                row = tbl[key]
                #self.logger.debug(f'IDX={idx} {key} : {row}')
                self.output_row(row)

        if self.csv_path is not None:
            self.csvfile.close()

    def output_row(self, row):
        if len(row[CSVEntry.ENCLOSED_BY]) > 0:
            enc = f'[{row[CSVEntry.ENCLOSED_BY]}]'
        else:
            enc = ''
        if self.csv_path is not None:
            # 0Place (ID), 1Title, 2Name, 3Type, 4latitude, 5longitude, 6enclosed_by
            title = GeoKeys.capwords(row[CSVEntry.TITLE])
            name = GeoKeys.capwords(row[CSVEntry.NAME])

            if math.isnan(float(row[CSVEntry.LAT])) or  math.isnan(float(row[CSVEntry.LAT])) :
                self.csvfile.write(f'[{row[CSVEntry.PLACE_ID]}],"{title}","{name}",{row[CSVEntry.TYPE]},'
                               f' , ,{enc},\n')
            else:
                self.csvfile.write(f'[{row[CSVEntry.PLACE_ID]}],"{title}","{name}",{row[CSVEntry.TYPE]},'
                               f'{row[CSVEntry.LAT]},{row[CSVEntry.LON]},{enc},\n')

    @staticmethod
    def retrieve_csv_place(admin_table, geodata, place: Loc.Loc, key, idx):
        # 0Place (ID), 1Title, 2Name, 3Type, 4latitude, 5longitude, 6enclosed_by
        row = admin_table[idx].get(key)
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
