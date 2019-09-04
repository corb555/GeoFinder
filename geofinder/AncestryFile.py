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

    def __init__(self, in_path: str, out_suffix: str, cache_dir, progress: Union[None, Progress.Progress]):
        self.build = False
        self.logger = logging.getLogger(__name__)
        self.progress_bar = progress
        self.output_latlon = True
        self.line_num: int = 0
        self.filesize = 0
        self.infile = None
        self.error = False
        self.out_path = in_path + out_suffix
        self.more_available = False

        self.value: str = ""
        self.tag: str = ""        # PLAC indicates this is a Place entry

        if out_suffix is not None:
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
            self.logger.info(f'Opened  {in_path}')
            self.error: bool = False
        else:
            self.logger.error(f"File {in_path} not found")
            self.error = True
        return self.error

    def get_next_place(self) -> (str, bool):
        # Scan file for Place Entry or EOF
        # Output all other lines as-is to outfile
        eof_reached = False
        town_entry = ''
        return town_entry, eof_reached

    def read_and_parse_line(self) -> Tuple[str, bool]:
        # Read a line from file.  Handle line.
        if not self.more_available:
            line = self.infile.readline()
        self.line_num += 1

        # update progress bar
        prog = int(self.infile.tell() * 100 / self.filesize)
        if self.line_num % 1000 == 1:
            self.progress(f"Scanning ", prog)

        if line == "":
            # End of File
            return "", True

        # Separate the line into  parts
        self.parse_line(line)

        #  Keep track of  lines for this event so we have full view of event
        self.collect_event_details()

        return line, False

    def parse_line(self, line: str):
        pass

    def collect_event_details(self):
        """ Collect details for event - last name, event date, and tag in GEDCOM file."""
        pass

    def peak_next_line(self):
        """ Return a peak at next line but dont move forward in file """
        pos = self.infile.tell()
        line = self.infile.readline()
        self.infile.seek(pos)  # Back up to where we were
        return line

    def output_place(self, txt):
        self.write(txt)

    def write(self, value: str):
        """ Write out a line.  Put together the pieces:  level, Label, tag, value """
        pass

    def write_lat_lon(self, lat: float, lon: float):
        """ Write out a GEDCOM PLACE MAP entry with latitude and longitude. """
        pass

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
