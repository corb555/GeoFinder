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


# todo get rid of set_grid_position from listboxframe
import collections
from typing import Dict

GridInfo = collections.namedtuple('GridInfo', 'col row xpad ypad sticky')
GridDict = Dict[str, GridInfo]

def set_grid_position(widget, name: str, grd: GridDict) -> None:
    """
    Lookup name of the widget in grd and position widget in a Tkinter grid layout using params in grd
    grd is a dictionary and
    each entry is a list of Col, row, xpad, ypad, sticky (optional).
    """
    # grd = {"title": [0, 0, 5, 10, "EW"], "progress": [0, 1, 5, 5, "EW"]}

    if grd[name][4] == " ":
        # No sticky value
        widget.grid(row=grd[name].row, column=grd[name][0], padx=grd[name][2],
                    pady=grd[name][3])
    else:
        widget.grid(row=grd[name][1], column=grd[name][0], padx=grd[name][2],
                    pady=grd[name][3], sticky=grd[name][4])