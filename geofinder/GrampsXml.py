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
import re
import xml.etree.ElementTree as Tree
from io import BytesIO
from typing import Union

from geofinder import Progress
from geofinder.AncestryFile import AncestryFile


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
    <placeobj handle="_e3e603bc19f6cdb5e7f5932562f" change="1567113428" id="P0000" type="City">
      <ptitle>Chelsea, Greater London, England, United Kingdom</ptitle>
      <pname value="Chelsea, Greater London, England, United Kingdom"/>
      <pname value="Chelsea district, Greater London, England, United Kingdom " lang="en">
         <dateval val="1987"/>
      </pname>
      <coord long="-0.16936" lat="51.48755"/>
      <placeref hlink="_e40b85dab5b634791e7788893c6"/>
    </placeobj>

    <placeobj handle="_e3e603bc1c94b85f1b59026fa08" change="1566106543" id="P0001" type="Unknown">
      <ptitle>Palo Alto, Santa Clara County, California, United States</ptitle>
      <pname value="Palo Alto, Santa Clara County, California, United States"/>
      <coord long="-122.14302" lat="37.44188"/>
    </placeobj>
    </places>

    xmllint --c14n one.xml > 1.xml
    """

    def __init__(self, in_path: str, out_suffix: str, cache_d, progress: Union[None, Progress.Progress]):
        super().__init__(in_path, out_suffix, cache_d, progress)
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
                # Got to end of tree.  Write out XML tree to tmp file
                tmp_name = self.out_path + '.tmp'
                self.elem.write(tmp_name)

                # Append XML tmp file to our output file
                self.append_file(tmp_name)
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
        # Find next placeobject entry in Tree
        # Each time we process a place, change XML tag to placeobj and set self.tag to PLAC

        # Find first placeobject
        self.place = self.elem.find('placeobject')

        if self.place is not None:
            #print(f'\n\nPLACEOBJECT {self.place.tag} =========')

            # Walk thru each entry in place object
            for place_entry in self.place.iter():
                self.child = place_entry
                #print(f'tag ={place_entry.tag}')
                if place_entry.tag == 'ptitle' and self.got_place is False:
                    # <ptitle>Chelsea, Greater London, England, United Kingdom</ptitle>
                    #print(f'PTITLE tag <{place_entry.tag}')
                    #print(f' entry {place_entry.text}')
                    self.tag = 'PLAC'
                    self.value = place_entry.text
                    self.got_place = True
                    return
                elif place_entry.tag == 'pname' and self.got_pname is False:
                    # <pname value="Chelsea, Greater London, England, United Kingdom"/>
                    self.tag = 'PLAC'
                    self.value = place_entry.get('value')
                    #print(f'PNAME <{place_entry.tag} VALUE="{self.value}"/>')
                    self.got_pname = True
                    return
                elif place_entry.tag == 'coord':
                    # <coord long="-0.16936" lat="51.48755"/>
                    self.lon = place_entry.attrib.get('long')
                    self.lat = place_entry.attrib.get('lat')
                    self.tag = 'IGNORE'
                    #print(f'<{place_entry.tag} LONG="{self.lon}" LAT="{self.lat}"/>')
                    self.place.remove(place_entry)
                else:
                    #print(f'DD <{place_entry.tag} {place_entry.attrib}>')
                    pass

            # Done walking through place element
            if self.lat != 99.9:
                # Create Coord Latitude/Longitude section
                coord_elem = Tree.Element("coord")
                coord_elem.set('long', str(self.lon))
                coord_elem.set('lat', str(self.lat))
                self.place.append(coord_elem)

            # Change tag back to 'placeobj' so we don't visit it next time we are called
            self.place.tag = 'placeobj'
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
            #print('TREE DONE')

    def write_updated(self, txt):
        # Update place entry in tree.  Tree will be written out later when entire XML tree is written out
        if self.child.text is not None:
            self.child.text = txt.strip(', ')
        else:
            if self.child.tag == 'pname':
                self.child.set('value', txt.strip(', '))

    def write_asis(self):
        # Do nothing - No change to place entry
        # It will be written out later when entire XML tree is written out
        pass

    def write_lat_lon(self, lat: float, lon: float):
        """ Create an XML lat/long coordinate enty """
        if self.output_latlon is False:
            return
        self.lat = lat
        self.lon = lon
