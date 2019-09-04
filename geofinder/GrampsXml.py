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
import xml.etree.ElementTree as Tree
from io import BytesIO
from pathlib import Path
from typing import Union, Tuple

from geofinder import GeoKeys, Progress
# for rank in root.iter('rank')
from geofinder.AncestryFile import AncestryFile


# State Machine
class State:
    PASS_THROUGH = 0
    COLLECT_PLACE_XML = 1
    WALK_PLACE_TREE = 2
    PLACE_TREE_COMPLETE = 3


class GrampsXml(AncestryFile):
    def __init__(self, in_path: str, out_suffix: str, cache_d, progress: Union[None, Progress.Progress]):
        super().__init__(in_path, out_suffix, cache_d, progress)
        self.root = None
        self.collect_lines = False
        self.place_xml_lines = b''
        self.state = State.PASS_THROUGH
        self.pl = None
        self.child = None

    def get_next_place(self) -> (str, bool):
        # BASE - DO NOT MODIFY *******

        # Scan  file for Place entry or EOF
        # Output all other lines as-is to outfile
        while True:
            line, err = self.read_and_parse_line()
            if err:
                return '', True  # End of file reached

            if self.tag == 'PLAC':
                # Found the target line.  Break out of loop
                entry = self.value
                if entry is None:
                    continue
                return entry, False
            else:
                # Not a target entry.   Write out line as-is
                if self.outfile is not None:
                    self.outfile.write(line)

    def read_and_parse_line(self) -> Tuple[str, bool]:
        # BASE - DO NOT MODIFY ********
        # Read a line from file.  Handle line.
        if not self.more_available:
            line = self.infile.readline()
            if line == "":
                # End of File
                return "", True
        else:
            line = ''

        self.line_num += 1

        # update progress bar
        prog = int(self.infile.tell() * 100 / self.filesize)
        if self.line_num % 1000 == 1:
            self.progress(f"Scanning ", prog)

        # Separate the line into  parts
        self.parse_line(line)

        #  Keep track of  lines for this event so we have full view of event
        self.collect_event_details()

        return line, False

    def parse_line(self, line: str):
        # Called by read_and_parse_line for each line in file
        if '<places>' in line:
            # Reached the start of Places XML section
            # Accumulate XML text until end of section
            self.state = State.COLLECT_PLACE_XML
        elif '</places>' in line:
            # Reached the end of Places section
            self.place_xml_lines += bytes(line, "utf8")
            print(f'xml len={len(self.place_xml_lines)}')

            # Build tree from XML string
            try:
                self.root = Tree.parse(BytesIO(self.place_xml_lines))
            except TypeError:
                print(f'XML parse error')
                self.root = None
            self.state = State.WALK_PLACE_TREE

        # Handle based on State
        self.tag = 'OTHER'
        if self.state == State.COLLECT_PLACE_XML:
            # Collect lines

            # Convert all placeobj tags to placeobject tag
            # This will allow us to keep track of which Place Objects we have processed.
            # As each is processed we convert it back to placeobj
            line = re.sub('placeobj', 'placeobject', line)

            self.place_xml_lines += bytes(line, "utf8")
        elif self.state == State.PASS_THROUGH:
            # Just output line
            pass
        elif self.state == State.WALK_PLACE_TREE:
            self.more_available = True
            self.walk_place_tree()
        elif self.state == State.PLACE_TREE_COMPLETE:
            # Write out XML tree
            self.root.write(self.out_path)
            self.state = State.PASS_THROUGH

    def walk_place_tree(self):
        # Find next place entry in Tree
        # Each time we process a place, add a completion indicator
        self.pl = self.root.find('placeobject')

        if self.pl is not None:
            print(self.pl.tag)
            self.pl.tag = 'placeobj'
            for child in self.pl.iter():
                self.child = child
                if child.text is not None:
                    print(f'AA <{child.tag}', end="")
                    print(f' {child.text}', end="")
                    self.tag = 'PLAC'
                    self.value = child.text
                    if 'Chiswick' in child.text:
                        child.text = 'Secretary,UK'
                    for key in child.attrib:
                        print(f' {key}="{child.attrib.get(key)}"', end="")
                    print('>')
                else:
                    if child.tag == 'pname':
                        self.tag = 'PLAC'
                        self.value = child.get('value')
                        print(f'BB <{child.tag} VALUE="{self.value}"/>')
                        if 'Chiswick' in self.value:
                            # pass
                            print('set')
                            child.set('value', 'Apple, France')
                        if 'Palo' in self.value:
                            a = Tree.Element("coord")
                            a.set('long', '71.1234')
                            a.set('lat', '1.34')
                            self.pl.append(a)
                    elif child.tag == 'coord':
                        lon = child.attrib.get('long')
                        lat = child.attrib.get('lat')
                        print(f'CC <{child.tag} LONG="{lon}" LAT="{lat}"/>')
                    else:
                        print(f'DD <{child.tag} {child.attrib}>')
        else:
            # No more place objects available
            self.state = State.PLACE_TREE_COMPLETE
            self.more_available = False

        print('PROCESS DONE')

    def output_place(self, txt):
        # Update place entry
        if self.child.text is not None:
            self.child.text = txt
        else:
            if self.child.tag == 'pname':
                self.child.set('value', txt)

    def write_lat_lon(self, lat: float, lon: float):
        """ Write out an XML lat/long coordinate enty """
        if self.output_latlon is False:
            return

        # Create Coord Latitude/Longitude section
        coord_elem = Tree.Element("coord")
        coord_elem.set('long', str(lon))
        coord_elem.set('lat', str(lat))
        self.pl.append(coord_elem)


cache_dir = os.path.join(str(Path.home()), GeoKeys.get_directory_name(), 'cache')
inpath = os.path.join(str(Path.home()), GeoKeys.get_directory_name(), 'cache', 'gramps.xml')
g_xml = GrampsXml(in_path=inpath, out_suffix='.out.xml', cache_d=cache_dir, progress=None)

# Read Gramps XML file: collect all place entries into b-string, output all else as-is.  Then parse the b-string
while True:
    # Find the next PLACE entry in  file
    # Process it and keep looping until we need user input
    town_entry, eof = g_xml.get_next_place()

    if eof:
        break
