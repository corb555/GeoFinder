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
import re
import xml.etree.ElementTree as Tree
from io import BytesIO
from typing import Union

from geofinder import Progress, Loc
from geofinder.AncestryFile import AncestryFile


# 0Place (ID), 1Title, 2Name, 3Type, 4latitude, 5longitude, enclosed_by

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


# State Machine
class State:
    PASS_THROUGH = 0
    COLLECT_PLACE_XML = 1
    WALK_PLACE_TREE = 2


class GrampsXml(AncestryFile):
    """
    Parse and update a Gramps XML DTD 1.7.1 file - sample of Place section below
    Gramps XML (Family Tree) - Not compressed, Not package

    https://www.gramps-project.org/xml/

    <places>
    <placeobj handle="_e3e603cc22486b8f5a7b6dda58" change="1571551969" id="P0565" type="County">
      <ptitle>Middlesex County, Massachusetts, United States</ptitle>
      <pname value="Middlesex County"/>
      <coord long="-71.39184" lat="42.48555"/>
      <placeref hlink="_e3e603bd7c12a78d92ba44844fd"/>
    </placeobj>

    <placeobj handle="_e3e603bc1c94b85f1b59026fa08" change="1566106543" id="P0001" type="Unknown">
      <ptitle>Palo Alto, Santa Clara County, California, United States</ptitle>
      <pname value="Palo Alto, Santa Clara County, California, United States"/>
      <coord long="-122.14302" lat="37.44188"/>
    </placeobj>
    </places>

    xmllint --c14n one.xml > 1.xml
    """

    def __init__(self, in_path: str, out_suffix: str, cache_d, progress: Union[None, Progress.Progress], geodata):
        super().__init__(in_path, out_suffix, cache_d, progress, geodata)
        self.elem = None
        self.collect_lines = False
        self.place_xml_lines = b''
        self.place = None
        self.child = None
        self.state = State.PASS_THROUGH  # Write out each line as-is unless we are in Place section
        self.got_pname = False
        self.got_place = False
        self.lon = 99.9
        self.lat = 99.9
        self.place_complete = 0
        self.admin_table = [{}, {}, {}, {}, {}]
        self.plac = None
        self.title = ''
        self.percent_complete = 0
        self.csvfile = None

    def parse_line(self, line: str):
        # Called by read_and_parse_line for each line in file
        # Accumulate all XML place entries into binary string, then build XML tree, then search XML tree
        # and return each entry in self.value with self.tag set to PLAC

        # Set State
        if '<places>' in line:
            # Reached the start of Places XML section.  Accumulate XML text until end of section
            self.state = State.COLLECT_PLACE_XML
        elif '</places>' in line:
            # Reached the end of Places section
            # TODO - Handle case where there is additional data on </places> line, such as '</places> <objects>'
            line += '\n'
            self.place_xml_lines += bytes(line, "utf8")
            self.logger.debug(f'xml len={len(self.place_xml_lines)}')

            # Build tree from XML string
            try:
                self.elem = Tree.parse(BytesIO(self.place_xml_lines))
            except TypeError:
                self.logger.warning(f'XML parse error')
                self.elem = None
            self.state = State.WALK_PLACE_TREE
            self.more_available = True

        # Handle line based on State
        self.tag = 'OTHER'

        if self.state == State.COLLECT_PLACE_XML:
            # Collect lines
            # Convert all placeobj tags to placeobject tag
            # As each is processed we convert it back to placeobj
            # This allows us to keep track of which Place Objects we have processed.
            if 'placeobj' in line:
                self.place_total += 1
            line = re.sub('placeobj', 'placeobject', line)
            self.place_xml_lines += bytes(line, "utf8")
            self.tag = 'IGNORE'
        elif self.state == State.PASS_THROUGH:
            #  output line in get_next_place
            pass
        elif self.state == State.WALK_PLACE_TREE:
            # Set self.value with next place
            self.find_xml_place()

            if not self.more_available:
                # Got to END OF TREE.  WRITE XML tree
                self.write_out_tree()
                self.complete_csv()

        return self.id

    def write_out_tree(self):
        # Write out XML tree
        tmp_name = self.out_path + '.tmp'
        self.elem.write(tmp_name)

        # Append XML tmp file to our output file
        self.append_file(tmp_name)

        # All additional text is pass through (not part of Place section)
        self.state = State.PASS_THROUGH

    def append_file(self, fname2):
        # Append file to our output
        self.outfile.flush()
        file2 = open(fname2, 'r')
        # Read in chunks
        while True:
            data = file2.read(65536)
            if data:
                self.outfile.write(data)
            else:
                break
        file2.close()
        self.outfile.write('\n')
        self.outfile.flush()

    def find_xml_place(self):
        # Find the next placeobject entry in Tree
        # Each time we process a place, change XML tag to placeobj and
        # set self.tag to PLAC so we don't handle again

        # Find first placeobject
        self.plac = self.elem.find('placeobject')

        if self.plac is not None:
            # print(f'\n\nPLACEOBJECT {self.place.tag} =========')
            self.id = self.plac.get("id")

            # Walk thru each entry in place object
            for place_entry in self.plac.iter():
                self.child = place_entry
                # print(f'tag ={place_entry.tag}')
                if place_entry.tag == 'ptitle' and self.got_place is False:
                    self.tag = 'PLAC'
                    self.value = place_entry.text
                    self.title = self.value
                    self.got_place = True
                    return
                elif place_entry.tag == 'pname' and self.got_pname is False:
                    # <pname value="Chelsea, Greater London, England, United Kingdom"/>
                    self.tag = 'PLAC'
                    self.value = place_entry.get('value')
                    self.name = self.value
                    # print(f'PNAME <{place_entry.tag} VALUE="{self.value}"/>')
                    self.got_pname = True
                    return
                elif place_entry.tag == 'coord':
                    # <coord long="-0.16936" lat="51.48755"/>
                    self.lon = place_entry.attrib.get('long')
                    self.lat = place_entry.attrib.get('lat')
                    self.tag = 'IGNORE'
                    # print(f'<{place_entry.tag} LONG="{self.lon}" LAT="{self.lat}"/>')
                    self.plac.remove(place_entry)
                else:
                    # print(f'DD <{place_entry.tag} {place_entry.attrib}>')
                    pass

            # Done walking through place element
            if self.lat != 99.9:
                # Create Coord Latitude/Longitude section
                coord_elem = Tree.Element("coord")
                coord_elem.set('long', str(self.lon))
                coord_elem.set('lat', str(self.lat))
                self.plac.append(coord_elem)

            # Change tag back to 'placeobj' so we don't visit it next time we are called
            self.plac.tag = 'placeobj'
            self.place_complete += 1
            # update progress bar
            self.percent_complete = int(self.place_complete * 100 / self.place_total)
            self.progress(f" ", self.percent_complete)

            # Reset values
            self.got_pname = False
            self.got_place = False
            self.lon = 99.9
            self.lat = 99.9
        else:
            # Tree completed.  No more place objects available
            self.more_available = False

    def write_updated(self, txt, place):
        # Update place entry in tree.  Tree will be written out later when entire XML tree is written out
        self.create_csv_node(place)
        if self.child.text is not None:
            self.child.text = txt.strip(', ')
        else:
            if self.child.tag == 'pname':
                self.child.set('value', txt.strip(', '))

    def write_asis(self):
        # Do nothing - No change to place entry
        # It will be written out later when entire XML tree is written out
        # TODO implement CSV
        self.logger.debug(f'AS IS {self.id} {self.value}')
        pass

    def write_lat_lon(self, lat: float, lon: float):
        """ Create an XML lat/long coordinate enty """
        if self.output_latlon is False:
            return
        self.lat = lat
        self.lon = lon

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
            raise Exception('Invalid place type')
        return dict_idx

    def get_enclosure_key(self, place):
        # Fill in admin2
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
            key = f'{place.city1}_{place.admin2_id}_{place.admin1_id}_{place.country_iso}'
        elif place.place_type == Loc.PlaceType.PREFIX:
            key = f'{place.prefix}_{place.city1}_{place.admin2_id}_{place.admin1_id}_{place.country_iso}'
        else:
            key = ''
        key = key.strip('_')
        self.logger.debug(f'key={key.upper().strip("_")} type={place.place_type}')

        return key.upper().strip('_')

    @staticmethod
    def clear_values(place):
        if place.place_type == Loc.PlaceType.COUNTRY:
            place.prefix = ''
            place.city1 = ''
            place.admin2_name = ''
            place.admin1_name = ''
        elif place.place_type == Loc.PlaceType.ADMIN1:
            place.prefix = ''
            place.city1 = ''
            place.admin2_name = ''
        elif place.place_type == Loc.PlaceType.ADMIN2:
            place.prefix = ''
            place.city1 = ''
        elif place.place_type == Loc.PlaceType.CITY:
            place.prefix = ''
        elif place.place_type == Loc.PlaceType.PREFIX:
            place.place_type = Loc.PlaceType.CITY

    def move_up_level(self, place, idx) -> bool:
        tokens = place.name.split(',')
        place.lat = 99.9
        place.lon = 99.9

        if place.place_type == Loc.PlaceType.COUNTRY:
            # Already at top
            place.feature = 'ADM0'
            return False
        elif place.place_type == Loc.PlaceType.ADMIN1:
            place.feature = 'ADM1'
            place.place_type = Loc.PlaceType.COUNTRY
        elif place.place_type == Loc.PlaceType.ADMIN2:
            place.feature = 'ADM2'
            place.place_type = Loc.PlaceType.ADMIN1
        elif place.place_type == Loc.PlaceType.CITY:
            place.place_type = Loc.PlaceType.ADMIN2
        elif place.place_type == Loc.PlaceType.PREFIX:
            place.place_type = Loc.PlaceType.CITY
            place.city1 = tokens[1]
        else:
            return False

        # Remove first token from name
        tkns = place.name.split(',')
        self.clear_values(place)
        place.name = place.format_full_nm(None)  # ','.join(tkns[1:])
        place.city1 = tkns[1]
        place.id = self.get_enclosure_key(place)

        dict_idx = self.get_dict_id(place)
        if dict_idx < idx:
            return True
        else:
            return False

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
            nm = ''
        return nm

    def create_csv_node(self, place: Loc.Loc):
        """
        Create CSV row in Dictionary:  Place (ID), Title, Name, Type, latitude, longitude,enclosed_by
        :param place:
        :return: None
        """
        if place.name == '':
            return

        row = [''] * 11
        # typ = place.feature_to_type()
        name_tokens = place.name.split(',')
        place.place_type = len(name_tokens) - 1
        row[CSVEntry.PLACE_ID] = place.id
        row[CSVEntry.ENCLOSED_BY] = place.enclosure_id

        self.geodata.find_first_match(place.name, place)
        place.id = row[CSVEntry.PLACE_ID]

        row[CSVEntry.TITLE] = place.name.title()
        row[CSVEntry.NAME] = self.get_csv_name(place).title()
        row[CSVEntry.FEAT] = place.feature
        row[CSVEntry.LAT] = f'{float(place.lat):.4f}'
        row[CSVEntry.LON] = f'{float(place.lon):.4f}'
        row[CSVEntry.ADMIN2_ID] = place.admin2_id
        row[CSVEntry.ADMIN1_ID] = place.admin1_id
        row[CSVEntry.ISO] = place.country_iso

        key = self.get_enclosure_key(place)
        dict_idx = self.get_dict_id(place)
        #node_id = place.id

        if 'P' in place.id:
            # our item has an ID with Pxxx,  add this row
            self.admin_table[dict_idx][key.upper()] = row
        else:
            res = self.admin_table[dict_idx].get(key.upper())
            if res is None:
                # Nothing there, add this row
                self.admin_table[dict_idx][key.upper()] = row
            else:
                # A node is already there and we don't have a P, so do nothing
                place.id = res[CSVEntry.PLACE_ID]

        self.logger.debug(f'\nUpdate CSV {key.upper()} idx={dict_idx}: {row}\n{place.name}')
        #return node_id

    def create_csv_enclosure(self, place: Loc.Loc, depth):
        """
        Create EnclosedBy elements in Dictionary for CSV file
        :return: None
        """
        self.logger.debug(f'\nCREATE ENCLOSURE name={place.name}')
        new_place = copy.copy(place)

        # recursively call until we reach Country level
        # Move up to enclosure level
        success = self.move_up_level(new_place, idx=self.get_dict_id(new_place))
        if success and depth < 7:
            self.create_csv_node(new_place)
            place.enclosure_id = new_place.id
            self.update_enclosure_id(place)

            self.create_csv_enclosure(new_place, depth=depth + 1)
        return

    def update_enclosure_id(self, place):
        key = self.get_enclosure_key(place)
        dict_idx = self.get_dict_id(place)
        row = self.admin_table[dict_idx].get(key.upper())
        if row:
            if 'P' not in row[CSVEntry.ENCLOSED_BY]:
                row[CSVEntry.ENCLOSED_BY] = place.enclosure_id
                self.admin_table[dict_idx][key.upper()] = row

    def copy_csv_to_place(self, place: Loc.Loc, key, idx):
        # 0Place (ID), 1Title, 2Name, 3Type, 4latitude, 5longitude, 6enclosed_by
        row = self.admin_table[idx].get(key)
        key_tokens = key.split("_")
        place.place_type = len(key_tokens) - 1
        self.logger.debug(f'{row}')
        place.feature = row[CSVEntry.FEAT]
        #place.place_type = row[CSVEntry.TYPE]
        #if place.place_type == '':
        #    place.feature_to_type()

        place.name = row[CSVEntry.TITLE]
        place.country_iso = row[CSVEntry.ISO]
        place.country_name = self.geodata.geo_files.geodb.get_country_name(place.country_iso)
        place.enclosure_id = row[CSVEntry.ENCLOSED_BY]

        place.lat: float = float(row[CSVEntry.LAT])
        place.lon: float = float(row[CSVEntry.LON])

        place.admin2_id = row[CSVEntry.ADMIN2_ID]
        place.admin1_id = row[CSVEntry.ADMIN1_ID]
        place.admin1_name = str(self.geodata.geo_files.geodb.get_admin1_name(place))
        place.admin2_name = str(self.geodata.geo_files.geodb.get_admin2_name(place))
        if place.admin2_name is None:
            place.admin2_name = ''
        if place.admin1_name is None:
            place.admin1_name = ''

        if place.place_type == Loc.PlaceType.CITY:
            place.city1 = row[CSVEntry.NAME]
        if place.place_type == Loc.PlaceType.PREFIX:
            place.prefix = row[CSVEntry.NAME]
        place.id = row[CSVEntry.PLACE_ID]

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
                self.copy_csv_to_place(place, key, idx)
                self.logger.debug(f'** CSV {key} {place.name}')

                # Recursively create enclosures above this
                self.create_csv_enclosure(place, depth=0)

        if self.csv_path is not None:
            self.csvfile = open(self.csv_path, "w", encoding='utf-8')
            self.logger.debug(f'CSV file {self.csv_path}')
            self.csvfile.write('Place,Title,Name,Type,latitude,longitude,enclosed_by\n')

        # List CSV
        self.logger.debug('*** TABLE ***')
        for idx, tbl in enumerate(self.admin_table):
            for key in tbl:
                # TODO
                row = tbl[key]
                # row = re.sub(r'\^',',',row)
                self.logger.debug(f'IDX={idx} {key} : {row}')
                self.output_row(row)

        if self.csv_path is not None:
            self.csvfile.close()

    def output_row(self, row):
        if self.csv_path is not None:
            # 0Place (ID), 1Title, 2Name, 3Type, 4latitude, 5longitude, 6enclosed_by
            self.csvfile.write(f'{row[CSVEntry.PLACE_ID]},"{row[CSVEntry.TITLE]}","{row[CSVEntry.NAME]}",{row[CSVEntry.TYPE]},'
                               f'{row[CSVEntry.LAT]},{row[CSVEntry.LON]},{row[CSVEntry.ENCLOSED_BY]},\n')
