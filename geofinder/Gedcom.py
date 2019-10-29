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
from typing import Match, Union

from geofinder import Progress
from geofinder.AncestryFile import AncestryFile
from geofinder.CachedDictionary import CachedDictionary

PLACE_TOTAL_KEY = 'PLACE_TOTAL'


class Gedcom(AncestryFile):
    """
    Class for Gedcom file handler - based on AncestryFile handler
    Basic routines to Read/Parse and Write GEDCOM ancestry files focused on place entries.
    Scan - Read through  file, find Place entry.
    Write out all other entries as-is if out_path is not None
    """

    def __init__(self, in_path: str, out_suffix: str, cache_d, progress: Union[None, Progress.Progress],geodata):
        super().__init__(in_path, out_suffix, cache_d, progress, geodata)

        # Sections of a GEDCOM line - Level, label, tag, value
        self.level: int = 0
        self.label: str = ""

        # Build dictionary of name/id pairs and write to pickle cache file.  If pickle file already there, just read it.
        # When we display a location, we use this to display the name the event is tied to
        parts = os.path.split(in_path)
        filename = parts[1] + '.pkl'
        self.person_cd = CachedDictionary(cache_d, filename)

        # Try to read pickle file of IDs for this GEDCOM file
        err = self.person_cd.read()
        if err:
            # File is not there.  Build it - it is a dictionary of GED Name_IDs to Names
            self.build_person_dictionary()
        else:
            # Get Place count from person dictionary
            self.place_total = self.person_cd.dict.get(PLACE_TOTAL_KEY)
            self.logger.debug(f'Place Total ={self.place_total}')

    def parse_line(self, line: str):
        # Called by read_and_parse_line for each line in file.  Parse line
        # and returns each place entry in self.value with self.tag set to PLAC

        # Gedcom file regex:          Digits for level,   @  for label,   text for tag,   text for value
        regex = re.compile(r"^(?P<level>\d+)\s+(?P<label>@\S+@)?\s*(?P<tag>\S+)\s+(?P<value>.*)")

        """ Parse GEDCOM line to Level, Label (if present), Tag, Value. """
        matches: Match = regex.match(line)

        if matches is not None:
            self.tag = matches.group('tag')  # GEDCOM tag
            self.level = int(matches.group('level'))  # GEDCOM level
            self.value = matches.group('value')  # GEDCOM value for command
            self.value = self.value.rstrip("\\")
            self.label = matches.group('label')  # GEDCOM label
        else:
            # Could not parse
            self.tag = ""
            self.value = ""
            self.level = 99
            self.label = ''

        # update progress bar
        self.percent_complete = int(self.infile.tell() * 100 / self.filesize)
        if self.line_num % 1000 == 1:
            self.progress(f"Scanning ", self.percent_complete)

        return self.id

    def write_updated(self, txt: str, place):
        """ Write out a place line with updated value.  Put together the pieces:  level, Label, tag, value """
        if self.outfile is not None:
            if self.label is not None:
                res = f"{self.level} {self.label} {self.tag} {txt.strip(', ')}\n"
            else:
                res = f"{self.level} {self.tag} {txt.strip(', ')}\n"

            self.outfile.write(res)

    def write_asis(self, entry):
        """ Write out a place line as-is.  Put together the pieces:  level, Label, tag, value """
        if self.outfile is not None:
            if self.label is not None:
                res = f"{self.level} {self.label} {self.tag} {self.value}\n"
            else:
                res = f"{self.level} {self.tag} {self.value}\n"

            self.outfile.write(res)

    def write_lat_lon(self, lat: float, lon: float):
        """ Write out a GEDCOM PLACE MAP entry with latitude and longitude. """
        if self.output_latlon is False:
            return

        if self.outfile is not None:
            map_level: int = self.level + 1
            lati_level: int = self.level + 2

            # Output Lat / Long
            if lon != float('NaN'):
                #  If there is already a MAP LATI LONG entry, eat it without output
                line: str = self.peak_next_line()
                self.parse_line(line)

                if self.tag == "MAP":
                    # Read this MAP command and do nothing with it
                    self.infile.readline()

                    # Check for LATI line
                    line = self.peak_next_line()
                    self.parse_line(line)
                    if self.tag == "LATI" or self.tag == "LONG":
                        # Read this LATI command and do nothing with it
                        self.infile.readline()

                    # Check for LONG line
                    line = self.peak_next_line()
                    self.parse_line(line)
                    if self.tag == "LATI" or self.tag == "LONG":
                        # Read this LONG command and do nothing with it
                        self.infile.readline()

                # Write out MAP Latitude/Longitude section
                self.outfile.write(f"{str(map_level)} MAP\n")
                self.outfile.write(f"{str(lati_level)} LATI {lat}\n")
                self.outfile.write(f"{str(lati_level)} LONG {lon}\n")

    def collect_event_details(self):
        """ Collect details for event - last name, event date, and tag in GEDCOM file."""

        # Text names for event tags
        event_names = {'DEAT': 'Death', 'CHR': 'Christening', 'BURI': 'Burial', 'BIRT': 'Birth',
                       'CENS': 'Census', 'MARR': 'Marriage', 'RESI': 'Residence', 'IMMI': 'Immigration', 'EMMI': 'Emmigration',
                       'OCCU': 'Occupation'}

        # Level of 0 indicates a new record - reset values
        if self.level == 0:
            self.id = ' '
            self.name = ''
            self.clear_date()

            if self.tag == 'INDI' or self.tag == 'FAM':
                if self.label is not None:
                    self.id = self.label
                    self.name = self.label
                    self.event_name = self.tag
                else:
                    self.logger.info(f'NO label line {self.line_num} tag {self.tag}')
        elif self.level == 1:
            self.clear_date()
            if self.tag == 'NAME':
                self.name = self.value
            if self.tag == 'HUSB':
                # We cheat on the Family tag and just use the Husbands name
                self.name = self.value
            # Store name of events that have Locations
            if self.tag in event_names:
                self.event_name = event_names[self.tag]
                self.clear_date()
            elif self.tag == 'TYPE':
                self.event_name = self.value
            elif self.tag != 'DATE' and self.tag != 'PLAC':
                self.event_name = self.tag
        elif self.level == 2:
            if self.tag == 'DATE':
                self.set_date(self.value)
            elif self.tag == 'TYPE':
                self.event_name = self.value

    def set_date(self, date: str):
        """ Set Date and Parse string for date/year and set Gedcom year of event """
        # Only supports simple date and ABT date, ignores date ranges
        self.date = date
        self.event_year = 0
        self.abt_flag = False  # Flag to indicate that this is an "ABOUT" date

        # Support DATE and ABT DATE of form <DD> <MMM> YYYY (GEDCOM format) with no validation
        reg = r'^\s*(ABT\s+)?([1-3]?[0-9]{1}\s+)?((JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+)?(\d{3,4})'

        m = re.search(reg, date)
        if m:
            abt = (m.group(1))
            # day = (m.group(2))
            # mon = (m.group(3))
            # group4 not used
            year = (m.group(5))

            if year is not None:
                self.event_year = int(year)
            if abt is not None:
                self.abt_flag = True

    def clear_date(self):
        self.event_year = 0
        self.date = ''

    def build_person_dictionary(self):
        """
        Read gedcom and extract Person names
        This is used to do lookup from ID to name
        """
        while True:
            line, err = self.read_and_parse_line()
            if err:
                break  # END OF FILE

            if self.tag == 'NAME' or self.tag == 'HUSB':
                # self.logger.debug(f'ky=[{self.id}] val=[{self.value}]')
                if self.id != self.value:
                    self.person_cd.dict[self.id] = self.value

            if self.tag == 'PLAC':
                self.place_total += 1

        # Save place total
        self.person_cd.dict[PLACE_TOTAL_KEY] = self.place_total
        self.logger.debug(f'Place Total ={self.place_total}')

        # Write out cached dictionary
        self.person_cd.write()

        # Done.  Reset file back to start
        self.infile.seek(0)
        self.line_num = 0
        self.logger.debug('build ged done')
        self.build = True

    def get_name(self, nam: str, depth: int = 0) -> str:
        # Get name of person we are currently on
        nm = self.person_cd.dict.get(nam)
        if nm is not None:
            if nm[0] == '@' and depth < 4:
                # Recursively call to get through the '@' indirect values.  make sure we don't go too deep
                nm = self.get_name(nm, depth + 1)
        else:
            nm = self.name

        self.logger.debug(f'{depth}) ky={self.id} {nm}: [{self.event_name}] [{self.date}]')

        return nm.replace('/', '')
