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
from typing import Union, Tuple

from geofinder import Progress


class AncestryFile:
    """
    Base class for Gedcom file handler and Gramps XML file handler
    Basic routines to Read/Parse and Write Ancestry files focused on place entries.
    Scan - Read through  file, find specified Tag entry.
    Write out all other entries as-is if out_path is not None
    """

    def __init__(self, in_path: str, out_suffix: str, cache_d, progress: Union[None, Progress.Progress], geodata):
        self.build = False
        self.logger = logging.getLogger(__name__)
        self.progress_bar = progress
        self.output_latlon = True
        self.filesize = 0
        self.infile = None
        self.error = False
        self.out_path = in_path + '.' + out_suffix
        self.geodata = geodata

        self.more_available = False

        self.place_total = 0
        self.line_num = 0

        self.value: str = ""
        self.tag: str = ""        # PLAC indicates this is a Place entry

        # GEDCOM  meta data
        self.id: str = ''
        self.name: str = ""
        self.event_year: int = 0
        self.event_name: str = ""
        self.date = ''
        self.abt_flag = False

        if out_suffix is not '':
            # Create an output file with same name with "out.ged" appended
            self.outfile = open(self.out_path, "w",
                                encoding='utf-8')
        else:
            self.outfile = None

        # Open Ancestry file in utf-8.  Replace any non-UTF-8 characters (e.g. Latin)
        err = self.open(in_path)
        if err:
            return

        if self.output_latlon is False:
            self.logger.warning('### OUTPUT OF LAT/LON IS DISABLED ###')

    def open(self, in_path) -> bool:
        # Open ancestry file
        if os.path.exists(in_path):
            self.infile = open(in_path, 'rU', encoding='utf-8', errors='replace')
            self.filesize: int = int(os.path.getsize(in_path))  # Used for progress bar calculation
            self.logger.info(f'Opened  {in_path} Size={self.filesize}')
            self.error: bool = False
        else:
            self.logger.error(f"File {in_path} not found")
            self.error = True
        return self.error

    def get_next_place(self) -> (str, bool):
        # Scan  file for Place entry or EOF
        # Output all other lines as-is to outfile
        while True:
            line, err, id = self.read_and_parse_line()
            if err:
                return '', True,''  # End of file reached

            if self.tag == 'PLAC':
                # Found the target line.  Break out of loop
                entry = self.value
                if entry is None:
                    continue
                return entry, False, id
            if self.tag == 'IGNORE':
                pass
            else:
                # Not a target entry.   Write out line as-is
                if self.outfile is not None:
                    self.outfile.write(line)

    def read_and_parse_line(self) -> Tuple[str, bool, str]:
        # Read a line from file.  Handle line.
        id =''
        if not self.more_available:
            line = self.infile.readline()
            self.line_num += 1
            if line == "":
                # End of File
                return "", True, id
        else:
            line = ''

        # Separate the line into  parts
        id = self.parse_line(line)

        #  Keep track of  lines for this event so we have full view of event
        self.collect_event_details()

        return line, False, id

    def collect_event_details(self):
        """ Collect details for event - last name, event date, and tag in GEDCOM file."""
        pass

    def peak_next_line(self):
        """ Return a peak at next line but dont move forward in file """
        pos = self.infile.tell()
        line = self.infile.readline()
        self.infile.seek(pos)  # Back up to where we were
        return line

    def close(self):
        self.infile.close()
        if self.outfile is not None:
            self.outfile.close()

    def progress(self, msg: str, percent: int):
        """ Display progress update """
        if percent < 2:
            percent = 2
        if self.progress_bar is not None:
            self.progress_bar.update_progress(percent, msg)
        else:
            self.logger.debug('prog is None')

    def get_name(self, nam: str, depth: int = 0) -> str:
        return ''

    # Derived classes must override these:

    def parse_line(self, line: str):
        # Called by read_and_parse_line for each line in file
        # return each entry in self.value with self.tag set to PLAC
        return self.id

    def write_updated(self, txt, place):
        """ Write updated place out """
        pass

    def write_asis(self, entry:str):
        """ Write out place entry as is.  """
        pass

    def write_lat_lon(self, lat: float, lon: float):
        """ Write out a GEDCOM PLACE MAP entry with latitude and longitude. """
        pass
