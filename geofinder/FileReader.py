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


class FileReader:
    """
    Read a file and call a handler for each line
    """

    def __init__(self, directory_name: str, filename: str, progress_bar):
        self.logger = logging.getLogger(__name__)
        self.directory: str = directory_name
        self.progress_bar = progress_bar
        self.fname: str = filename
        self.cache_changed = False

    def read(self) -> bool:
        """
        :synopsis:  Read geoname.org alternate name file and add names as alternates in geoname dict
        :return: Error
        """
        count = 0
        line_num = 0
        file_pos = 0

        path = os.path.join(self.directory, self.fname)
        self.logger.info(f"Reading file {path}")
        if os.path.exists(path):
            fsize = os.path.getsize(path)
            with open(path, 'r', newline="", encoding='utf-8', errors='replace') as file:
                for row in file:
                    line_num += 1
                    file_pos += len(row)
                    if line_num % 80000 == 1:
                        # Periodically update progress
                        prog = file_pos * 100 / fsize
                        self.progress(f"Loading {self.fname} {prog:.0f}%", prog)

                    self.handle_line(line_num, row)

            self.cache_changed = True
            self.progress("", 100)
            self.logger.info(f'Added {count} items')
            return False
        else:
            self.logger.error(f'Unable to open {path}')
            return True

    def handle_line(self, line_num: int, row: str) -> int:
        pass

    def progress(self, msg, val):
        """ Update progress bar if there is one """
        if val < 2:
            val = 2
        if self.progress_bar is not None:
            self.progress_bar.update_progress(val, msg)

        self.logger.debug(msg)
