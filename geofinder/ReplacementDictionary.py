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


GEOID_TOKEN = 1
PREFIX_TOKEN = 2

def build_replacement_entry(geoid, prefix):
    """
    Build replacement dictionary entry
    Args:
        geoid: 
        prefix: 
    Returns:

    """
    return '@' + geoid + '@' + prefix

def parse_replacement_entry(entry) -> (str, str):
    """
    Parse replacement dictionary entry.  
    Args:
        entry: replacement dictionary entry

    Returns:

    """
    # Format is  @GEOID@PREFIX
    if entry is None:
        return '',''
    else:
        rep_token = entry.split('@')
        if len(rep_token) < 2:
            return ('', '')
    
        geoid = rep_token[GEOID_TOKEN]
        # Get prefix if there was one
        if len(rep_token) > 2:
            prefix = rep_token[PREFIX_TOKEN]
        else:
            prefix = ''
    
        return prefix, geoid
