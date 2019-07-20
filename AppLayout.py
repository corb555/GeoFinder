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
import tkinter.font
import tkinter
from tkinter import *
from tkinter import ttk
from typing import List

import Progress
import Tooltip
from Widge import Widge

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

FNT = 'Helvetica'
FNT_SIZE_SM = 8
FNT_SIZE_MD = 14
FNT_SIZE_LG = 18
FNT_SIZE_XL = 24

# Columns for widgets
PAD_COL = 0
TXT_COL = 1
SCRL_COL = 2
BTN_COL = 3


class AppLayout:

    def __init__(self, main):
        """ Create the app window and styles """
        self.logger = logging.getLogger(__name__)
        self.main = main
        self.window = tkinter.Tk()
        self.window.title("GeoFinder")
        self.window["padx"] = 0
        self.window["pady"] = 20
        self.window.configure(background=BG_COLOR)

        # Set column/row weight for responsive resizing
        self.window.columnconfigure(0, weight=1)
        for rw in range(0, 12):
            self.window.rowconfigure(rw, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure('.', font=(FNT, FNT_SIZE_MD))  # Default button font

        # Create styles
        style.configure('Error.TLabel', foreground=ERR_COLOR, background=BG_COLOR, font=(FNT, FNT_SIZE_LG))
        style.configure('Good.TLabel', foreground=GOOD_COLOR, background=BG_COLOR, font=(FNT, FNT_SIZE_LG))
        style.configure('Info.TLabel', foreground=FG_COLOR, background=BG_COLOR, font=(FNT, FNT_SIZE_MD))
        style.configure('Info.TLabel', foreground=FG_COLOR, background=BG_COLOR, font=(FNT, FNT_SIZE_MD))
        style.configure('Highlight.TLabel', foreground=HIGH_COLOR, background=BG_COLOR, font=(FNT, FNT_SIZE_MD))

        style.configure('Large.TLabel', foreground=HIGH_COLOR, background=BG_COLOR, font=(FNT, FNT_SIZE_XL))
        style.configure('Light.TLabel', borderwidth=3, foreground=LT_COLOR, background=BG_COLOR, font=(FNT, FNT_SIZE_MD))
        style.configure('Tiny.TLabel', borderwidth=3, foreground=LT_COLOR, background=BG_COLOR, font=(FNT, FNT_SIZE_SM))
        style.configure('TEntry', foreground=FG_COLOR)
        style.configure('TButton', foreground=FG_COLOR)
        style.configure('Preferred.TButton', foreground=GOOD_COLOR)

        # Load images for buttons
        try:
            self.search_image = tkinter.PhotoImage(file="images/search.gif")
            self.map_image = tkinter.PhotoImage(file="images/map.gif")
            self.verify_image = tkinter.PhotoImage(file="images/verify.gif")
            self.save_image = tkinter.PhotoImage(file="images/save.gif")
            self.skip_image = tkinter.PhotoImage(file="images/skip.gif")
            self.help_image = tkinter.PhotoImage(file="images/help.gif")
            self.exit_image = tkinter.PhotoImage(file="images/exit.gif")
            self.load_image = tkinter.PhotoImage(file="images/play.gif")
            self.folder_image = tkinter.PhotoImage(file="images/folder.gif")
        except Exception as e:
            self.logger.debug(f'Missing Button Image files. {e}')

        self.window.update()

    def create_initialization_widgets(self):
        """ Create the  widgets for display during initialization """
        self.pad: ttk.Label = ttk.Label(self.window, text=" ", width=2, style='Light.TLabel')

        self.title: ttk.Label = ttk.Label(self.window, text="Geo Finder", width=30, style='Large.TLabel')
        self.line_number_label: ttk.Label = ttk.Label(self.window, text="", width=BTN_WID, style='Tiny.TLabel')

        self.original_entry: ttk.Label = ttk.Label(self.window, text=" ", width=50, style='Info.TLabel')
        self.status: ttk.Label = ttk.Label(self.window, width=TXT_WID, style='Good.TLabel')

        self.prog: Progress.Progress = Progress.Progress(self.window, bar_color=HIGH_COLOR, trough_color=LT_GRAY, status=self.status)

        self.quit_button: ttk.Button = ttk.Button(self.window, text="quit", command=self.main.shutdown,
                                                  width=BTN_WID_WD, image=self.exit_image, compound="left")
        self.load_button: ttk.Button = ttk.Button(self.window, text="open", command=self.main.load_handler,
                                                  width=BTN_WID_WD, style='Preferred.TButton', image=self.load_image, compound="left")
        self.change_button: ttk.Button = ttk.Button(self.window, text="choose", command=self.main.filename_handler,
                                                    width=BTN_WID_WD, image=self.folder_image, compound="left")

        # Set grid layout for padding column widget - just pads out left column
        self.pad.grid(column=PAD_COL, row=0, padx=PAD_PADX, pady=0, sticky="EW")

        # Set grid for text widgets
        self.original_entry.grid(column=TXT_COL, row=2, padx=7, pady=5, sticky="EW")
        self.status.grid(column=TXT_COL, row=4, padx=7, pady=5, sticky="EW")
        self.title.grid(column=TXT_COL, row=0, padx=7, pady=12, sticky="")
        self.prog.bar.grid(column=TXT_COL, row=1, padx=7, pady=5, sticky="EW")

        # Set grid for button widgets
        # self.line_number_label.grid(column=SCRL_COL, row=1, padx=7, pady=6, sticky="")
        self.load_button.grid(column=SCRL_COL, row=2, padx=20, pady=6, sticky="")
        self.change_button.grid(column=SCRL_COL, row=3, padx=20, pady=6, sticky="")
        self.quit_button.grid(column=SCRL_COL, row=9, padx=20, pady=6, sticky="S")

        Tooltip.Tooltip(self.window, self.load_button, text="Open GEDCOM file")
        Tooltip.Tooltip(self.window, self.change_button, text="Choose GEDCOM file")

        self.window.update()

        self.initialization_buttons: List[ttk.Button] = [self.quit_button, self.load_button, self.change_button]
        Widge.disable_buttons(button_list=self.initialization_buttons)

    def remove_initialization_widgets(self):
        self.load_button.destroy()
        self.change_button.destroy()
        self.quit_button.destroy()
        self.title.destroy()
        self.prog.bar.destroy()

    def create_review_widgets(self):
        self.remove_initialization_widgets()  # Remove old widgets

        """ Create all the buttons and entry fields for normal running """
        self.pad: ttk.Label = ttk.Label(self.window, text=" ", width=2, style='Light.TLabel')
        self.title: ttk.Label = ttk.Label(self.window, text="Geo Finder", width=30, style='Large.TLabel')

        self.original_entry: ttk.Label = ttk.Label(self.window, text="   ", width=TXT_WID, style='Light.TLabel')
        self.user_edit: ttk.Entry = ttk.Entry(self.window, text="   ", width=TXT_WID, font=(FNT, 14))
        self.status: ttk.Label = ttk.Label(self.window, width=TXT_WID, style='Good.TLabel')
        self.prefix: ttk.Label = ttk.Label(self.window, width=TXT_WID, style='Highlight.TLabel')

        self.scrollbar = ttk.Scrollbar(self.window)
        self.listbox = tkinter.Listbox(self.window, height=15, bg=LT_GRAY, borderwidth=0, selectmode=SINGLE)
        self.listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.listbox.yview)

        self.ged_event_info: ttk.Label = ttk.Label(self.window, text=" ", width=TXT_WID, style='Light.TLabel')
        self.line_number_label: ttk.Label = ttk.Label(self.window, text="", width=6, style='Light.TLabel')
        self.footnote: ttk.Label = ttk.Label(self.window, text="Data is from GeoNames.org.  Hover for details",
                                             width=TXT_WID, style='Light.TLabel')

        self.prog: Progress.Progress = Progress.Progress(self.window, bar_color=HIGH_COLOR, trough_color=LT_GRAY, status=self.status)

        self.search_button: ttk.Button = ttk.Button(self.window, text="search", command=self.main.search_handler,
                                                    width=BTN_WID, image=self.search_image, compound="left")
        self.map_button: ttk.Button = ttk.Button(self.window, text="map", command=self.main.map_handler,
                                                 width=BTN_WID, image=self.map_image, compound="left")
        self.verify_button: ttk.Button = ttk.Button(self.window, text="verify", command=self.main.verify_handler,
                                                    width=BTN_WID, image=self.verify_image, compound="left")
        self.save_button: ttk.Button = ttk.Button(self.window, text="save", command=self.main.save_handler,
                                                  width=BTN_WID, image=self.save_image, compound="left")
        self.skip_button: ttk.Button = ttk.Button(self.window, text="skip", command=self.main.skip_handler, width=BTN_WID,
                                                  image=self.skip_image, compound="left")
        self.help_button: ttk.Button = ttk.Button(self.window, text="help", command=self.main.help_handler,
                                                  width=BTN_WID, image=self.help_image, compound="left")
        self.quit_button: ttk.Button = ttk.Button(self.window, text=" quit", command=self.main.quit_handler,
                                                  width=BTN_WID, image=self.exit_image, compound="left")

        # Set grid layout for padding column widget - just pads out left column
        self.pad.grid(column=PAD_COL, row=0, padx=PAD_PADX, pady=0, sticky="EW")

        # Set grid layout for  Text column Widgets
        # The first set span 2 columns because the listbox has a scrollbar next to it
        self.ged_event_info.grid(column=TXT_COL, row=7, padx=0, pady=6, sticky="W", columnspan=2)
        self.title.grid(column=TXT_COL, row=0, padx=0, pady=12, sticky="N", columnspan=2)
        self.prog.bar.grid(column=TXT_COL, row=1, padx=0, pady=5, sticky="EW", columnspan=2)
        self.original_entry.grid(column=TXT_COL, row=2, padx=0, pady=5, sticky="EWS", columnspan=2)
        self.user_edit.grid(column=TXT_COL, row=3, padx=0, pady=0, sticky="EWN", columnspan=2)
        self.prefix.grid(column=TXT_COL, row=4, padx=0, pady=0, sticky="EW", columnspan=2)
        self.status.grid(column=TXT_COL, row=5, padx=0, pady=0, sticky="EW", columnspan=2)
        self.listbox.grid(column=TXT_COL, row=6, padx=0, pady=5, sticky="EW")
        self.footnote.grid(column=TXT_COL, row=12, padx=0, pady=5, sticky="EW")

        # Column 1 - just scrollbar
        self.scrollbar.grid(column=SCRL_COL, row=6, padx=0, pady=5, sticky='WNS')

        # column 2 Widgets
        self.search_button.grid(column=BTN_COL, row=2, padx=BTN_PADX, pady=6, sticky="E")
        self.verify_button.grid(column=BTN_COL, row=3, padx=BTN_PADX, pady=6, sticky="E")
        self.save_button.grid(column=BTN_COL, row=4, padx=BTN_PADX, pady=6, sticky="E")
        self.map_button.grid(column=BTN_COL, row=5, padx=BTN_PADX, pady=6, sticky="NE")
        self.skip_button.grid(column=BTN_COL, row=6, padx=BTN_PADX, pady=6, sticky="E")
        self.help_button.grid(column=BTN_COL, row=8, padx=BTN_PADX, pady=5, sticky="E")
        self.quit_button.grid(column=BTN_COL, row=12, padx=BTN_PADX, pady=6, sticky="SE")

        # Set accelerator keys for Verify, listbox, and Save
        self.user_edit.bind("<Return>", self.main.return_key_event_handler)
        self.user_edit.bind("<Control-s>", self.main.ctl_s_event_handler)
        self.user_edit.bind("<FocusIn>", self.main.entry_focus_event_handler)
        self.listbox.bind("<FocusIn>", self.main.list_focus_event_handler)

        # Tooltips
        footnote_text = 'This uses data from GeoNames.org. This work is licensed under a Creative Commons Attribution 4.0 License,\
         see https://creativecommons.org/licenses/by/4.0/ The Data is provided "as is" without warranty or any representation of accuracy, \
         timeliness or completeness.'
        Tooltip.Tooltip(self.window, self.footnote, text=footnote_text)
        Tooltip.Tooltip(self.window, self.ged_event_info, text="Person and Event in GEDCOM")
        Tooltip.Tooltip(self.window, self.original_entry, text="Original GEDCOM entry")
        Tooltip.Tooltip(self.window, self.verify_button, text="Verify new entry")
        Tooltip.Tooltip(self.window, self.search_button, text="Bring up search in browser")
        Tooltip.Tooltip(self.window, self.map_button, text="Bring up map in browser")
        Tooltip.Tooltip(self.window, self.save_button, text="Save this replacement")
        Tooltip.Tooltip(self.window, self.line_number_label, text="GEDCOM line number")
        Tooltip.Tooltip(self.window, self.skip_button, text="Ignore this error and write out unmodified")

        self.review_buttons: List[ttk.Button] = [self.save_button, self.search_button, self.verify_button,
                                                 self.skip_button, self.map_button, self.help_button]

        self.window.update()
