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
from tkinter.ttk import Progressbar


class Progress:
    """ Create a progress bar for loading large files or other long operations """

    def __init__(self, window, bar_color, trough_color, status):
        self.window = window

        style: ttk.Style = ttk.Style()
        style.configure("bar.Horizontal.TProgressbar",
                        troughcolor=trough_color, bordercolor='white',
                        background=bar_color, lightcolor=bar_color, darkcolor=bar_color)

        self.bar: Progressbar = Progressbar(window, length=400, maximum=100, style="bar.Horizontal.TProgressbar")
        self.bar['value'] = 2
        self.lable = status
        self.startup: bool = True

        # Call appropriate update loop depending on whether we have entered main window loop
        if self.startup:
            self.window.update()  # Still in startup mode.  Use stronger window.update
        else:
            self.window.update_idletasks()

    def update_progress(self, progress: int, stage: str):
        if progress < 2:
            progress = 2
        self.bar['value'] = progress
        self.lable.set_text(stage)
        if self.startup:
            self.window.update()
        else:
            self.window.update_idletasks()

    def destroy(self):
        self.bar.destroy()
        self.window.update_idletasks()
