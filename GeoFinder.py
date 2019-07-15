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
import copy
import logging
import os
import sys
import webbrowser
from pathlib import Path
from tkinter import filedialog, END
from tkinter import messagebox

import AppLayout
import Gedcom
import GeoKeys
import Geodata
import Place
from CachedDictionary import CachedDictionary
from Config import Config
from Widge import Widge


class GeoFinder:
    """
    Read in a GEDCOM genealogy file and verify that the spelling of each place is correct.
    If place is found, add the latitude and longitude to the output GEDCOM file.
    If place cant be found, allow the user to correct it.  If it is corrected, apply the change to all matching entries.
    Also allow the user to mark an item to skip if a resolution cant be found.
    Skiplist is a list of locations the user has flagged to skip.  These items will be ignored
    Global replace list is list of fixes the user has found.  Apply these to any new similar matches.
        
    Uses gazetteer files from geoname.org as the reference source.  Uses English modern place names, plus some county aliases.

    Main classes:

    GeoFinder3 - The main app
    GeoData - The geonames.org data and lookup
    GEDCOM - routines to read and write GEDCOM
    """

    def __init__(self):
        print('GeoFinder3')
        self.logger = None
        self.shutdown_requested: bool = False  # Flag to indicate user requested shutdown
        self.save_enabled = False  # Do we have a valid match that we can save?
        self.setup_logging('GeoFinder3 Init')
        self.directory: str = os.path.join(str(Path.home()), Geodata.Geodata.get_directory_name())
        self.cache_dir = GeoKeys.cache_directory(self.directory)
        self.user_selected_list = False

        # Get configuration settings
        self.logger.debug('load config')
        self.cfg = Config()
        err = self.cfg.read(self.cache_dir, "config.pkl")
        if err:
            self.logger.warning(f'error reading {self.cache_dir} config.pkl')

        pathname = self.cfg.get("gedcom_path")
        out_path = pathname + "new.ged"
        cdir = self.cache_dir
        self.gedcom: Gedcom.Gedcom(in_path=pathname, out_path=out_path, cache_dir=cdir, progress=None) = None
        self.place: Place.Place = Place.Place()

        # Create App window and configure  window buttons and widgets
        self.w: AppLayout.AppLayout = AppLayout.AppLayout(self)
        self.w.create_initialization_widgets()

        # Read in Skiplist, Replace list and  Already Accepted list
        # self.w.window.update()
        self.skiplist = CachedDictionary(self.cache_dir, "skiplist.pkl")
        self.skiplist.read()
        self.global_replace = CachedDictionary(self.cache_dir, "global_replace.pkl")
        self.global_replace.read()
        self.user_accepted = CachedDictionary(self.cache_dir, "accepted.pkl")  # List of items that have been accepted
        self.user_accepted.read()

        # Initialize geodata
        self.geodata = Geodata.Geodata(directory_name=self.directory, progress_bar=self.w.prog)
        error = self.geodata.read()
        if error:
            Widge.fatal_error("Missing Files.  Run Setup.py and correct in Files Tab")

        # If the list of supported countries is unusually short, display note to user
        num = self.display_country_note()
        self.logger.info(f'{num} countries will be loaded')

        # Read in Geoname Gazeteer file - city names, lat/long, etc.
        error = self.geodata.read_geonames()
        if error:
            Widge.fatal_error("Missing Files.  Run Setup.py and correct in Files Tab")
        self.logger.info(f'Geoname dictionary has {self.geodata.geo_files.geodb.get_stats()} entries')
        self.w.window.update()
        self.w.prog.update_progress(100, " ")

        # Prompt user to click Open for GEDCOM file
        Widge.set_text(self.w.original_entry, self.cfg.get("gedcom_path"))
        Widge.enable_buttons(self.w.initialization_buttons)
        if os.path.exists(self.cfg.get("gedcom_path")):
            Widge.set_text(self.w.status, "Click Open to load GEDCOM file")
        else:
            # GEDCOM file name isn't valid - prompt user to select
            self.w.load_button.config(state="disabled")
            Widge.set_text(self.w.status, "Choose GEDCOM file")

        self.startup = False  # Flag to indicate whether we are in startup or in Window loop.  Determines how window idle is called
        self.w.window.mainloop()  # ENTER MAIN LOOP and Wait for user to click on load button

    def load_handler(self):
        """
        User pressed LOAD button to load a GEDCOM file. Load in file name and
        loop through GEDCOM file and find every PLACe entry and verify the entry against the geoname data
        """
        Widge.set_text(self.w.original_entry, "")
        self.w.create_review_widgets()  # Get rid of File widgets and display main review widgets

        # Open and parse GEDCOM file
        ged_path = self.cfg.get("gedcom_path")
        self.gedcom = Gedcom.Gedcom(in_path=ged_path, out_path=ged_path + '.new.ged', cache_dir=self.cache_dir,
                                    progress=self.w.prog)  # Routines to open and parse GEDCOM file
        self.w.window.update()
        if self.gedcom.error:
            Widge.fatal_error(f"GEDCOM file {ged_path} not found.  Run Setup.py and correct in Config Tab")

        # Add GEDCOM filename to Title
        path_parts = os.path.split(ged_path)
        Widge.set_text(self.w.title, f'GeoFinder3 - {path_parts[1]}')

        # Read GEDCOM file, find each place entry and handle it.
        self.handle_place_entry()

    def handle_place_entry(self):
        """ Get next PLACE  in users GED File.  Replace it, skip it, or have user correct it. """
        Widge.set_text(self.w.original_entry, "")
        Widge.set_text(self.w.status, "Scanning...")
        self.clear_detail_text(self.place)

        while True:
            # Find the next PLACE entry in GEDCOM file and Keep looping until we need user input
            town_entry, eof = self.gedcom.scan_for_tag('PLAC')
            self.w.window.update_idletasks()

            if eof:
                # End of file reached
                Widge.disable_buttons(button_list=self.w.review_buttons)
                Widge.set_text(self.w.status, "Done.  Shutting Down...")
                Widge.set_text(self.w.original_entry, " ")
                path = self.cfg.get("gedcom_path")
                messagebox.showinfo("Info", f"Finished GEDCOM file.\n\nWriting results to\n {path}.new.ged")
                self.logger.info('End of GEDCOM file')
                self.shutdown()

            # Parse the entry into Prefix, City, District2, District1, Country
            self.place.parse_place(place_name=town_entry, geo_files=self.geodata.geo_files)
            self.w.status.configure(style="Good.TLabel")

            # When we find an error, see if we have a fix (Global Replace) or Skip (ignore). Otherwise have user handle
            if self.global_replace.get(self.place.name) is not None:
                # There is a global change that we can apply to this line.  Get the replacement text
                replacement = self.global_replace.get(self.place.name)
                self.logger.debug(f'Global Replace found: [{replacement}]')

                # get lat long and add to gedcom output file
                self.geodata.find_location(replacement, self.place)
                self.gedcom_output_place(self.place)
                self.gedcom.write_lat_lon(lat=self.place.lat, lon=self.place.lon)

                # Display status to user
                Widge.set_text(self.w.user_edit, replacement)
                Widge.set_text(self.w.status, "Applying previous change")

                if self.shutdown_requested:
                    self.set_detail_text_line("Shutting down...")
                continue
            elif self.shutdown_requested:
                # User requested shutdown.  Finish up going thru file, then shut down
                self.set_detail_text_line("Shutting Down...")
                Widge.set_text(self.w.original_entry, " ")
                self.gedcom.write(self.place.name)
                continue
            elif self.skiplist.get(self.place.name) is not None:
                # item is in skiplist - Skip it and go to next error
                self.logger.debug('SkipList match found')
                Widge.set_text(self.w.user_edit, self.place.name)
                Widge.set_text(self.w.status, "Skipping")
                self.gedcom.write(self.place.name)
                continue
            else:
                # Found a new item
                # See if its in our place database
                self.geodata.find_location(town_entry, self.place)

                if self.place.result_type in GeoKeys.successful_match:
                    # Found a match
                    if self.user_accepted.get(self.place.name) is not None:
                        # User has already accepted this match
                        # Write out line without user verification
                        self.logger.debug('Accepted ')
                        self.gedcom_output_place(self.place)
                        self.gedcom.write_lat_lon(self.place.lat, self.place.lon)
                        continue
                    else:
                        break  # Have user review the match
                else:
                    # Place not found.  Break out of loop.  We have an error to look at.
                    break

        # Have user review the result
        Widge.set_text(self.w.original_entry, self.place.name)
        self.display_result(self.place)

    def verify_handler(self):
        """ Verify if the users new Place entry has a match in geonames data.  """
        self.logger.debug("   *** VERIFY ***")

        # Do we verify item from listbox or text edit field?
        if self.user_selected_list:
            # User selected item from listbox - get listbox selection
            town_entry = self.w.listbox.get(self.w.listbox.curselection())
            # Update the user edit widget with the List selection item
            Widge.set_text(self.w.user_edit, town_entry)
            # self.logger.debug(f'selection = {town_entry}')
            # Get unique match
            self.geodata.find_first_match(town_entry, self.place)
        else:
            # User typed in text entry window - get edit field value
            town_entry: str = self.w.user_edit.get()
            self.geodata.find_location(town_entry, self.place)

        self.display_result(self.place)

    def skip_handler(self):
        """ Write out original entry and skip any matches in future  """
        self.skiplist.set(Widge.get_text(self.w.original_entry), " ")
        self.gedcom.write(Widge.get_text(self.w.original_entry))

        # Save Skip info for future runs
        self.skiplist.write()
        self.handle_place_entry()

    def save_handler(self):
        """ Save the Place as user updated it.  Add Place to global replace list and replace if we see it again. """

        # Save in global replace list if user made a change.  This will be cached to disk.
        if Widge.get_text(self.w.original_entry) != Widge.get_text(self.w.user_edit):
            # User made a change - save it
            self.global_replace.set(Widge.get_text(self.w.original_entry), Widge.get_text(self.w.user_edit))
            # Save fix for future runs
            self.global_replace.write()
        else:
            # User accepted the item as is.
            self.user_accepted.set(Widge.get_text(self.w.original_entry), "")
            self.user_accepted.write()

        # Write out corrected item to GEDCOM output file
        self.gedcom_output_place(self.place)

        # Get next error
        self.handle_place_entry()

    @staticmethod
    def help_handler():
        """ Bring up browser with help text """
        help_base = "https://github.com/corb555/GeoFinder/wiki/User-Guide"
        webbrowser.open(help_base)

    def search_handler(self):
        """ Bring up browser with Google search with this item """
        base = "https://www.google.com/search?q="
        loc = Widge.get_text(self.w.user_edit)
        webbrowser.open(f"{base}{loc}")

    def map_handler(self):
        """ Bring up browser with map for this item """
        base = "http://www.openstreetmap.org"
        if self.place.place_type == Place.PlaceType.COUNTRY or self.place.place_type == Place.PlaceType.ADMIN1:
            # Zoom wide if user just put in state, country
            zoom = "zoom=7"
        else:
            zoom = "zoom=14"
        loc = f"{base}/?mlat={self.place.lat}&mlon={self.place.lon}&{zoom}#map={self.place.lat}/{self.place.lon}"
        webbrowser.open(loc)

    def quit_handler(self):
        """ Set flag for shutdown.  Process all global replaces and exit """
        if messagebox.askyesno(' ', '   Exit?'):
            Widge.disable_buttons(button_list=self.w.review_buttons)
            self.w.quit_button.config(state="disabled")
            self.w.prog.startup = True

            Widge.set_text(self.w.user_edit, " ")
            Widge.set_text(self.w.status, "Quitting...")
            # Write out the item we are on
            self.gedcom.write(Widge.get_text(self.w.original_entry))
            self.shutdown_requested = True

            # We will still continue to go through file, but only handle global replaces
            self.handle_place_entry()

    def filename_handler(self):
        """ Display file selector dialog """
        fname = filedialog.askopenfilename(initialdir=self.directory,
                                           title="Select GEDCOM file",
                                           filetypes=(("GEDCOM files", "*.ged"), ("all files", "*.*")))
        if len(fname) > 1:
            self.cfg.set("gedcom_path", fname)  # Add filename to dict
            self.cfg.write()  # Write out config file
            self.w.load_button.config(state="normal")
            Widge.set_text(self.w.status, "Click Open to load GEDCOM file")
            Widge.set_text(self.w.original_entry, self.cfg.get("gedcom_path"))

    def display_result(self, place):
        # Found an item that requires user intervention
        self.w.user_edit.focus()  # Set focus to text edit widget

        # Enable buttons so user can either click Skip, or edit the item and Click Verify.
        Widge.enable_buttons(self.w.review_buttons)
        Widge.set_text(self.w.user_edit, place.name)
        self.logger.debug(f'disp result.  list= {place.georow_list}')

        # Found an error
        if place.result_type == GeoKeys.Result.MULTIPLE_MATCHES or \
                place.result_type == GeoKeys.Result.NO_MATCH or \
                place.result_type == GeoKeys.Result.NO_COUNTRY:
            # Disable the Save & Map button until user clicks Verify and item is found in gazeteer
            self.disable_save(True)
            self.w.verify_button.configure(style="Preferred.TButton")  # Make the Verify button the preferred selection
            self.w.save_button.configure(style="TButton")  # Make the Save button normal
        elif place.result_type == GeoKeys.Result.NOT_SUPPORTED or place.result_type == GeoKeys.Result.EXACT_MATCH or \
                place.result_type == GeoKeys.Result.PARTIAL_MATCH:
            # Found a match or Not supported
            self.disable_save(False)  # Enable save button
            self.w.verify_button.configure(style="TButton")  # Make the Verify button normal
            self.w.save_button.configure(style="Preferred.TButton")  # Make the Save button the preferred selection
        else:
            self.logger.debug(f'unk typ={place.result_type}')

        if place.result_type in GeoKeys.successful_match:
            self.w.status.configure(style="Good.TLabel")
        else:
            self.w.status.configure(style="Error.TLabel")

        self.set_status_text(place.get_status())
        if len(place.prefix) > 0:
            Widge.set_text(self.w.prefix, 'PREFIX= ' + place.prefix)
        else:
            Widge.set_text(self.w.prefix, ' ')

        if len(place.georow_list) > 0:
            # self.logger.debug(f'len={len(place.georow_list)}')
            self.display_georow_list(place)
        else:
            self.set_detail_text_line(place.status_detail)

        # Display GED person and event
        Widge.set_text(self.w.ged_event_info, f'{self.gedcom.get_name(self.gedcom.id)}: {self.gedcom.last_tag_name} {self.gedcom.date}')
        self.w.window.update_idletasks()

    def display_georow_list(self, place: Place.Place):
        """ Display latest status or error detail """
        # self.logger.debug(f'display georow list ')

        # Load in list and display
        self.w.listbox.delete(0, END)

        """
        # [(0 city, 1 country, 2 dist1, 3 dist2, ), (prefix, city, dist2, dist1, country)]
        # Sort by Dist1, then Dist2, then city

        for item in sorted(place.georow_list, key=itemgetter(2, 1, 0)):
            tx = ', '.join(item)
            self.w.listbox.insert(END, f"{tx}")
        """
        # Iterate list and lookup admin names and format
        # Output to display
        lkp_place = copy.copy(place)
        output_list = []

        for item in place.georow_list:
            # self.logger.debug(f'{item}')
            self.geodata.geo_files.geodb.get_geodata(item, lkp_place)
            nm = lkp_place.get_placename()
            output_list.append(f'{place.prefix}{nm}')

        # Output to display
        for item in output_list:
            self.w.listbox.insert(END, item)
            # self.logger.debug(f'display georow list {item}')

        self.w.window.update_idletasks()

    def return_key_event_handler(self, event):
        """ User pressed Return accelerator key.  Call Verify data entry """
        self.verify_handler()
        return "break"

    def entry_focus_event_handler(self, event):
        # Track focus so when user presses Verify, we know whether to get text from Entry Box or List box
        self.user_selected_list = False

    def list_focus_event_handler(self, event):
        # Track focus so when user presses Verify, we know whether to get text from Entry Box or List box
        self.user_selected_list = True

    def ctl_s_event_handler(self, event):
        """ User pressed Ctrl-S Save accelerator key.  Call Save  """
        if self.save_enabled:
            self.save_handler()
        return "break"

    def clear_detail_text(self, place):
        self.set_detail_text_line(" ")
        self.w.listbox.insert(END, " ")
        self.w.listbox.delete(0, END)
        place.georow_list.clear()

    def set_detail_text_line(self, txt):
        self.logger.debug(f'display detail txt [{txt}]')
        self.w.listbox.delete(0, END)
        self.w.listbox.insert(END, txt)

    def display_country_note(self) -> int:
        countries, num = self.geodata.geo_files.get_supported_countries()
        self.w.window.update()
        if num == 0:
            Widge.fatal_error("No countries enabled.\n\nUse Setup.py Country Tab to change country list\n")

        if num < 20:
            messagebox.showinfo("Info", "{}{}{}".format("Loaded geocode data for the following countries:\n\n",
                                                        countries,
                                                        "\n\nUse Setup.py Country Tab to change country list\n"))
        return num

    def setup_logging(self, msg):
        self.logger = logging.getLogger(__name__)
        fmt = "%(levelname)s %(name)s.%(funcName)s %(lineno)d: %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=fmt)
        self.logger.info(msg)

    def gedcom_output_place(self, place: Place.Place):
        # Format location and write out to gedcom file
        self.gedcom.write(place.prefix + place.get_placename())
        self.logger.debug(f'gcom wr {place.prefix}{place.get_placename()}')

    def shutdown(self):
        """ Shutdown - write out Gbl Replace and skip file and exit """
        self.w.window.update_idletasks()
        # self.geodata.write()
        self.skiplist.write()
        self.global_replace.write()
        self.user_accepted.write()
        self.cfg.write()
        if self.gedcom is not None:
            self.gedcom.close()
        self.w.window.quit()
        sys.exit()

    def disable_save(self, disable: bool):
        if disable:
            # Disable the Save and Map buttons
            self.save_enabled = False
            self.w.save_button.config(state="disabled")
            self.w.map_button.config(state="disabled")
        else:
            # Enable the Save and Map buttons
            self.save_enabled = True
            self.w.save_button.config(state="normal")  # Match - enable  button
            self.w.map_button.config(state="normal")  # Match - enable  button

    def set_status_text(self, txt):
        # status text is readonly
        self.w.status.state(["!readonly"])
        Widge.set_text(self.w.status, txt)
        self.w.status.state(["readonly"])


r = GeoFinder()
