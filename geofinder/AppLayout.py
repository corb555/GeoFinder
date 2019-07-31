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
import tkinter as tk
from tkinter import ttk
from typing import List

import pkg_resources

import geofinder.GFStyle as GFStyle
import geofinder.Widge
from geofinder import Progress, Tooltip

# Columns for widgets:
# [0 PADDING]  [1 TEXT    with span 2]  [3 Buttons]
#                       [2 Scroll Bar]
PAD_COL = 0
TXT_COL = 1
SCRL_COL = 2
BTN_COL = 3


class AppLayout:

    def __init__(self, main):
        """ Create the app window and styles """
        self.logger = logging.getLogger(__name__)
        self.main = main

        self.root = tk.Tk()
        self.root.title("GEOfinder")
        self.root["padx"] = 0
        self.root["pady"] = 20

        # Set column/row weight for responsive resizing
        self.root.columnconfigure(0, weight=1)
        for rw in range(0, 12):
            self.root.rowconfigure(rw, weight=1)

        # Setup styles
        self.root.configure(background=GFStyle.BG_COLOR)
        GFStyle.GFStyle()

        # Load images for buttons
        self.images = {}
        for icon_name in ("map", "verify", "save", "skip", "help", "exit", "play", "folder", "search"):
            path = pkg_resources.resource_filename(__name__, f'images/{icon_name}.gif')
            self.images[icon_name] = tk.PhotoImage(file=path)

        self.root.update()

    def create_initialization_widgets(self):
        """ Create the  widgets for display during initialization  (File open)  """
        self.pad: geofinder.Widge.CLabel = geofinder.Widge.CLabel(self.root, text=" ", width=2, style='Light.TLabel')
        self.title: geofinder.Widge.CLabel = geofinder.Widge.CLabel(self.root, text="GEO FINDER", width=30, style='Large.TLabel')
        self.original_entry: geofinder.Widge.CLabel = geofinder.Widge.CLabel(self.root, text=" ", width=50, style='Info.TLabel')
        self.status: geofinder.Widge.CLabel = geofinder.Widge.CLabel(self.root, width=GFStyle.TXT_WID, style='Good.TLabel')
        self.prog: Progress.Progress = Progress.Progress(self.root, bar_color=GFStyle.HIGH_COLOR, trough_color=GFStyle.LT_GRAY, status=self.status)
        self.quit_button: ttk.Button = ttk.Button(self.root, text="quit", command=self.main.shutdown,
                                                  width=GFStyle.BTN_WID_WD, image=self.images['exit'], compound="left")
        self.load_button: ttk.Button = ttk.Button(self.root, text="open", command=self.main.load_handler,
                                                  width=GFStyle.BTN_WID_WD, style='Preferred.TButton', image=self.images['play'], compound="left")
        self.change_button: ttk.Button = ttk.Button(self.root, text="choose", command=self.main.filename_handler,
                                                    width=GFStyle.BTN_WID_WD, image=self.images['folder'], compound="left")

        # Set grid layout for padding column widget - just pads out left column
        self.pad.grid(column=PAD_COL, row=0, padx=GFStyle.PAD_PADX, pady=0, sticky="EW")

        # Set grid for text widgets
        self.original_entry.grid(column=TXT_COL, row=2, padx=7, pady=5, sticky="EW")
        self.status.grid(column=TXT_COL, row=4, padx=7, pady=5, sticky="EW")
        self.title.grid(column=TXT_COL, row=0, padx=7, pady=12, sticky="")
        self.prog.bar.grid(column=TXT_COL, row=1, padx=7, pady=5, sticky="EW")

        # Set grid for button widgets
        self.load_button.grid(column=SCRL_COL, row=2, padx=20, pady=6, sticky="")
        self.change_button.grid(column=SCRL_COL, row=3, padx=20, pady=6, sticky="")
        self.quit_button.grid(column=SCRL_COL, row=9, padx=20, pady=6, sticky="S")

        Tooltip.Tooltip(self.root, self.load_button, text="Open GEDCOM file")
        Tooltip.Tooltip(self.root, self.change_button, text="Choose GEDCOM file")

        self.root.update()

        self.initialization_buttons: List[ttk.Button] = [self.quit_button, self.load_button, self.change_button]
        geofinder.Widge.Widge.disable_buttons(button_list=self.initialization_buttons)

    def remove_initialization_widgets(self):
        self.load_button.destroy()
        self.change_button.destroy()
        self.quit_button.destroy()
        self.title.destroy()
        self.prog.bar.destroy()

    def create_review_widgets(self):
        self.remove_initialization_widgets()  # Remove old widgets

        """ Create all the buttons and entry fields for normal running """
        self.pad: geofinder.Widge.CLabel = geofinder.Widge.CLabel(self.root, text=" ", width=2, style='Light.TLabel')
        self.title: geofinder.Widge.CLabel = geofinder.Widge.CLabel(self.root, text="GEO FINDER", width=30, style='Large.TLabel')

        self.original_entry: geofinder.Widge.CLabel = geofinder.Widge.CLabel(self.root, text="   ", width=GFStyle.TXT_WID, style='Light.TLabel')
        self.user_entry: geofinder.Widge.CEntry = geofinder.Widge.CEntry(self.root, text="   ", width=GFStyle.TXT_WID, font=(GFStyle.FNT_NAME, 14))
        self.status: geofinder.Widge.CLabel = geofinder.Widge.CLabel(self.root, width=GFStyle.TXT_WID, style='Good.TLabel')
        self.prefix: geofinder.Widge.CLabel = geofinder.Widge.CLabel(self.root, width=GFStyle.TXT_WID, style='Highlight.TLabel')

        self.scrollbar = ttk.Scrollbar(self.root)

        self.tree = ttk.Treeview(self.root, style="Plain.Treeview", selectmode="browse")
        self.tree.tag_configure('odd', background=GFStyle.ODD_ROW_COLOR)
        self.tree.tag_configure('even', background='white')

        self.tree["columns"] = ("pre",)
        self.tree.column("#0", width=500, minwidth=100, stretch=tk.NO)
        self.tree.column("pre", width=180, minwidth=5, stretch=tk.NO)
        self.tree.heading("#0", text="   Location", anchor=tk.W)
        self.tree.heading("pre", text="   Prefix", anchor=tk.W)

        self.tree.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.tree.yview)

        self.ged_event_info: geofinder.Widge.CLabel = geofinder.Widge.CLabel(self.root, text=" ", width=GFStyle.TXT_WID, style='Light.TLabel')
        self.footnote: geofinder.Widge.CLabel = geofinder.Widge.CLabel(self.root, text="Data is from GeoNames.org.  Hover for details",
                                                                       width=GFStyle.TXT_WID, style='Light.TLabel')

        self.prog: Progress.Progress = Progress.Progress(self.root, bar_color=GFStyle.HIGH_COLOR, trough_color=GFStyle.LT_GRAY, status=self.status)

        self.search_button: ttk.Button = ttk.Button(self.root, text="search", command=self.main.search_handler,
                                                    width=GFStyle.BTN_WID, image=self.images['search'], compound="left")
        self.map_button: ttk.Button = ttk.Button(self.root, text="map", command=self.main.map_handler,
                                                 width=GFStyle.BTN_WID, image=self.images['map'], compound="left")
        self.verify_button: ttk.Button = ttk.Button(self.root, text="verify", command=self.main.verify_handler,
                                                    width=GFStyle.BTN_WID, image=self.images['verify'], compound="left")
        self.save_button: ttk.Button = ttk.Button(self.root, text="save", command=self.main.save_handler,
                                                  width=GFStyle.BTN_WID, image=self.images['save'], compound="left")
        self.skip_button: ttk.Button = ttk.Button(self.root, text="skip", command=self.main.skip_handler, width=GFStyle.BTN_WID,
                                                  image=self.images['skip'], compound="left")
        self.help_button: ttk.Button = ttk.Button(self.root, text="help", command=self.main.help_handler,
                                                  width=GFStyle.BTN_WID, image=self.images['help'], compound="left")
        self.quit_button: ttk.Button = ttk.Button(self.root, text=" quit", command=self.main.quit_handler,
                                                  width=GFStyle.BTN_WID, image=self.images['exit'], compound="left")

        # Set grid layout for padding column widget - just pads out left column
        self.pad.grid(column=PAD_COL, row=0, padx=GFStyle.PAD_PADX, pady=0, sticky="EW")

        # Set grid layout for column 0 (TXT_COL) Widgets
        # The first 8 are set span to 2 columns because the listbox has a scrollbar next to it
        self.title.grid(column=TXT_COL, row=0, padx=0, pady=12, sticky="N", columnspan=2)
        self.prog.bar.grid(column=TXT_COL, row=1, padx=0, pady=5, sticky="EW", columnspan=2)
        self.original_entry.grid(column=TXT_COL, row=2, padx=0, pady=5, sticky="EWS", columnspan=2)
        self.user_entry.grid(column=TXT_COL, row=3, padx=0, pady=0, sticky="EWN", columnspan=2)
        self.status.grid(column=TXT_COL, row=4, padx=0, pady=0, sticky="EW", columnspan=2)
        self.tree.grid(column=TXT_COL, row=5, padx=0, pady=5, sticky="EW")
        self.ged_event_info.grid(column=TXT_COL, row=7, padx=0, pady=6, sticky="W", columnspan=2)
        self.footnote.grid(column=TXT_COL, row=12, padx=0, pady=5, sticky="EW", columnspan=2)

        # Column 1 - just the scrollbar
        self.scrollbar.grid(column=SCRL_COL, row=5, padx=0, pady=5, sticky='WNS')

        # Column 2 Widgets
        self.map_button.grid(column=BTN_COL, row=1, padx=GFStyle.BTN_PADX, pady=6, sticky="NE")
        self.search_button.grid(column=BTN_COL, row=2, padx=GFStyle.BTN_PADX, pady=6, sticky="E")
        self.verify_button.grid(column=BTN_COL, row=4, padx=GFStyle.BTN_PADX, pady=6, sticky="E")
        self.save_button.grid(column=BTN_COL, row=5, padx=GFStyle.BTN_PADX, pady=6, sticky="NE")
        self.skip_button.grid(column=BTN_COL, row=6, padx=GFStyle.BTN_PADX, pady=6, sticky="E")
        self.help_button.grid(column=BTN_COL, row=8, padx=GFStyle.BTN_PADX, pady=5, sticky="E")
        self.quit_button.grid(column=BTN_COL, row=12, padx=GFStyle.BTN_PADX, pady=6, sticky="SE")

        # Set accelerator keys for Verify, listbox, and Save
        self.user_entry.bind("<Return>", self.main.return_key_event_handler)
        self.user_entry.bind("<Control-s>", self.main.ctl_s_event_handler)

        # Track whether user is in Edit box or list box
        self.user_entry.bind("<FocusIn>", self.main.entry_focus_event_handler)
        self.tree.bind("<FocusIn>", self.main.list_focus_event_handler)

        # Tooltips
        footnote_text = 'This uses data from GeoNames.org. This work is licensed under a Creative Commons Attribution 4.0 License,\
         see https://creativecommons.org/licenses/by/4.0/ The Data is provided "as is" without warranty or any representation of accuracy, \
         timeliness or completeness.'
        Tooltip.Tooltip(self.root, self.footnote, text=footnote_text)
        Tooltip.Tooltip(self.root, self.ged_event_info, text="Person and Event in GEDCOM")
        Tooltip.Tooltip(self.root, self.original_entry, text="Original GEDCOM entry")
        Tooltip.Tooltip(self.root, self.verify_button, text="Verify new entry")
        Tooltip.Tooltip(self.root, self.search_button, text="Bring up search in browser")
        Tooltip.Tooltip(self.root, self.map_button, text="Bring up map in browser")
        Tooltip.Tooltip(self.root, self.save_button, text="Save this replacement")
        Tooltip.Tooltip(self.root, self.skip_button, text="Ignore this error and write out unmodified")

        self.review_buttons: List[ttk.Button] = [self.save_button, self.search_button, self.verify_button,
                                                 self.skip_button, self.map_button, self.help_button]

        self.root.update()
