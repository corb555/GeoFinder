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
from tkinter import ttk

TXT_WID = 65
BTN_WID = 5
BTN_WID_WD = 6

BTN_PADX = 50
PAD_PADX = 25

LT_GRAY = 'gray97'
LT_COLOR = 'gray50'
FG_COLOR = 'gray29'
BG_COLOR = "white"
HIGH_COLOR = 'royalblue3'
ERR_COLOR = 'red2'
GOOD_COLOR = 'green4'
ODD_ROW_COLOR = '#E8E8f8'

FNT_NAME = 'Helvetica'

FNT_SIZE_SM = 8
FNT_SIZE_MD = 14
FNT_SIZE_LG = 16
FNT_SIZE_XL = 24


class GFStyle:
    """ Tk Styles for GeoFinder and GeoUtil """

    def __init__(self):
        styl = ttk.Style()

        styl.theme_use("clam")
        styl.configure('.', font=(FNT_NAME, FNT_SIZE_MD))  # Default button font

        styl.configure('Large.TLabel', foreground=HIGH_COLOR, background=BG_COLOR, font=(FNT_NAME, FNT_SIZE_XL))

        styl.configure('Error.TLabel', foreground=ERR_COLOR, background=BG_COLOR, font=(FNT_NAME, FNT_SIZE_LG))
        styl.configure('Good.TLabel', foreground=GOOD_COLOR, background=BG_COLOR, font=(FNT_NAME, FNT_SIZE_LG))
        styl.configure('GoodCounty.TLabel', foreground=HIGH_COLOR, background=BG_COLOR, font=(FNT_NAME, FNT_SIZE_LG))

        styl.configure('Info.TLabel', foreground=FG_COLOR, background=BG_COLOR, font=(FNT_NAME, FNT_SIZE_MD))
        styl.configure('Highlight.TLabel', foreground=HIGH_COLOR, background=BG_COLOR, font=(FNT_NAME, FNT_SIZE_MD))
        styl.configure('Light.TLabel', borderwidth=3, foreground=LT_COLOR, background=BG_COLOR,
                       font=(FNT_NAME, FNT_SIZE_MD))

        styl.configure('Tiny.TLabel', borderwidth=3, foreground=LT_COLOR, background=BG_COLOR,
                       font=(FNT_NAME, FNT_SIZE_SM))

        styl.configure('TEntry', foreground=FG_COLOR)

        styl.configure('TButton', foreground=FG_COLOR)
        styl.configure('Preferred.TButton', foreground=GOOD_COLOR)

        styl.configure("Plain.Treeview", highlightthickness=0, bd=0, font=(FNT_NAME, FNT_SIZE_MD),
                       foreground=FG_COLOR)  # Modify the font of the body
        styl.configure("Plain.Treeview.Heading", font=(FNT_NAME, FNT_SIZE_MD, 'bold'),
                       foreground=FG_COLOR, background=LT_GRAY, relief="flat")  # Modify the font of
        # the headings
        styl.layout("Plain.Treeview", [('Plain.Treeview.treearea', {'sticky': 'nswe'})])  # Remove the borders

        # Import the Notebook.tab element from the default theme
        styl.element_create('Plain.Notebook.tab', "from", 'default')
        # Redefine the TNotebook Tab layout to use the new element
        styl.layout("TNotebook.Tab",
                    [('Plain.Notebook.tab', {'children':
                                                 [('Notebook.padding', {'side': 'top', 'children':
                                                     [('Notebook.focus', {'side': 'top', 'children':
                                                         [('Notebook.label', {'side': 'top', 'sticky': ''})],
                                                                          'sticky': 'nswe'})],
                                                                        'sticky': 'nswe'})],
                                             'sticky': 'nswe'})])
        styl.configure("TNotebook", background=BG_COLOR, borderwidth=0)
        styl.configure("TNotebook.Tab", background="purple", foreground=FG_COLOR,
                       lightcolor='red', borderwidth=0)
        styl.configure("TFrame", background=BG_COLOR, foreground=FG_COLOR, borderwidth=0)
