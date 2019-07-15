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
from typing import Dict

# special help to simplify entering UK items
great_britain = ['scotland', 'england', 'wales', 'northern ireland']


class Country:
    def __init__(self, progress):
        self.logger = logging.getLogger(__name__)
        self.progress = progress
        self.country_dict: Dict[str, str] = {}  # Dictionary of Country Name to country iso code
        self.iso_dict: Dict[str, str] = {}  # Reverse dictionary - Country ISO code to country name

    def get_name(self, country_iso: str) -> str:
        """ return country name for specified ISO code """
        return self.iso_dict.get(country_iso.lower())

    def get_iso(self, name: str) -> str:
        """ Return ISO code for specified country"""
        return self.country_dict.get(name.lower())

    @staticmethod
    def in_great_britain(country) -> bool:
        """ Determine if country is in Great Britain """
        return country in great_britain

    def read(self) -> bool:
        """
        Read in list of country names and ISO codes
        todo read countries from file
        """
        if self.progress is not None:
            self.progress.update_progress(100, "Read ISO countries...")

        # list of all countries and their ISO codes
        # This also includes some common aliases
        c_dict = {"Afghanistan": "AF",
                  "Albania": "AL",
                  "Algeria": "DZ",
                  "American Samoa": "AS",
                  "Andorra": "AD",
                  "Angola": "AO",
                  "Anguilla": "AI",
                  "Antarctica": "AQ",
                  "Antigua": "AG",
                  "Argentina": "AR",
                  "Armenia": "AM",
                  "Aruba": "AW",
                  "Australia": "AU",
                  "Austria": "AT",
                  "Azerbaijan": "AZ",
                  "Bahamas": "BS",
                  "Bahrain": "BH",
                  "Bangladesh": "BD",
                  "Barbados": "BB",
                  "Barbuda": "AG",
                  "Belarus": "BY",
                  "Belgium": "BE",
                  "Belize": "BZ",
                  "Benin": "BJ",
                  "Bermuda": "BM",
                  "Bhutan": "BT",
                  "Bolivia": "BO",
                  "Bonaire": "BQ",
                  "Bosnia and Herzegovina": "BA",
                  "Botswana": "BW",
                  "Bouvet Island": "BV",
                  "Brazil": "BR",
                  "British Indian Ocean Territory": "IO",
                  "British Virgin Islands": "VG",
                  "Brunei Darussalam": "BN",
                  "Bulgaria": "BG",
                  "Burkina Faso": "BF",
                  "Burundi": "BI",
                  "Cambodia": "KH",
                  "Cameroon": "CM",
                  "Canada": "CA",
                  "Cape Verde": "CV",
                  "Cayman Islands": "KY",
                  "Central African Republic": "CF",
                  "Chad": "TD",
                  "Chile": "CL",
                  "China": "CN",
                  "Christmas Island": "CX",
                  "Cocos Islands": "CC",
                  "Colombia": "CO",
                  "Comoros": "KM",
                  "Congo": "CG",
                  "Cook Islands": "CK",
                  "Costa Rica": "CR",
                  "Cote D'Ivoire": "CI",
                  "Croatia": "HR",
                  "Cuba": "CU",
                  "Curaçao": "CW",
                  "Cyprus": "CY",
                  "Czech Republic": "CZ",
                  "Czechoslovakia": "CZ",
                  "Côte d’Ivoire": "CI",
                  "Democratic Republic of the Congo": "CD",
                  "Denmark": "DK",
                  "Djibouti": "DJ",
                  "Dominica": "DM",
                  "Dominican Republic": "DO",
                  "Ecuador": "EC",
                  "Egypt": "EG",
                  "El Salvador": "SV",
                  "Equatorial Guinea": "GQ",
                  "Eritrea": "ER",
                  "Estonia": "EE",
                  "Ethiopia": "ET",
                  "Falkland Islands": "FK",
                  "Faroe Islands": "FO",
                  "Fiji": "FJ",
                  "Finland": "FI",
                  "France": "FR",
                  "French Guiana": "GF",
                  "French Polynesia": "PF",
                  "French Southern Territories": "TF",
                  "Gabon": "GA",
                  "Gambia": "GM",
                  "Georgia": "GE",
                  "Germany": "DE",
                  "Ghana": "GH",
                  "Gibraltar": "GI",
                  "Great Britain": "GB",
                  "Greece": "GR",
                  "Greenland": "GL",
                  "Grenada": "GD",
                  "Guadeloupe": "GP",
                  "Guam": "GU",
                  "Guatemala": "GT",
                  "Guernsey": "GG",
                  "Guinea": "GN",
                  "Guinea-Bissau": "GW",
                  "Guyana": "GY",
                  "Haiti": "HT",
                  "Heard Island and McDonald Islands": "HM",
                  "Honduras": "HN",
                  "Hong Kong": "HK",
                  "Hungary": "HU",
                  "Iceland": "IS",
                  "India": "IN",
                  "Indonesia": "ID",
                  "Iran": "IR",
                  "Iraq": "IQ",
                  "Ireland": "IE",
                  "Isle of Man": "IM",
                  "Israel": "IL",
                  "Italy": "IT",
                  "Jamaica": "JM",
                  "Japan": "JP",
                  "Jersey": "JE",
                  "Jordan": "JO",
                  "Kazakhstan": "KZ",
                  "Kenya": "KE",
                  "Kiribati": "KI",
                  "Kuwait": "KW",
                  "Kyrgyzstan": "KG",
                  "Lao": "LA",
                  "Latvia": "LV",
                  "Lebanon": "LB",
                  "Lesotho": "LS",
                  "Liberia": "LR",
                  "Libya": "LY",
                  "Liechtenstein": "LI",
                  "Lithuania": "LT",
                  "Luxembourg": "LU",
                  "Macao": "MO",
                  "Macedonia": "MK",
                  "Madagascar": "MG",
                  "Malawi": "MW",
                  "Malaysia": "MY",
                  "Maldives": "MV",
                  "Mali": "ML",
                  "Malta": "MT",
                  "Marshall Islands": "MH",
                  "Martinique": "MQ",
                  "Mauritania": "MR",
                  "Mauritius": "MU",
                  "Mayotte": "YT",
                  "Mexico": "MX",
                  "Micronesia": "FM",
                  "Moldova": "MD",
                  "Monaco": "MC",
                  "Mongolia": "MN",
                  "Montenegro": "ME",
                  "Montserrat": "MS",
                  "Morocco": "MA",
                  "Mozambique": "MZ",
                  "Myanmar": "MM",
                  "Namibia": "NA",
                  "Nauru": "NR",
                  "Nepal": "NP",
                  "Netherlands": "NL",
                  "New Caledonia": "NC",
                  "New Zealand": "NZ",
                  "Nicaragua": "NI",
                  "Niger": "NE",
                  "Nigeria": "NG",
                  "Niue": "NU",
                  "Norfolk Island": "NF",
                  "North Korea": "KP",
                  "Northern Mariana Islands": "MP",
                  "Norway": "NO",
                  "Oman": "OM",
                  "Pakistan": "PK",
                  "Palau": "PW",
                  "Palestine": "PS",
                  "Panama": "PA",
                  "Papua New Guinea": "PG",
                  "Paraguay": "PY",
                  "Peru": "PE",
                  "Philippines": "PH",
                  "Pitcairn": "PN",
                  "Poland": "PL",
                  "Portugal": "PT",
                  "Puerto Rico": "PR",
                  "Qatar": "QA",
                  "Romania": "RO",
                  "Russian Federation": "RU",
                  "Russia": "RU",
                  "Rwanda": "RW",
                  "Réunion": "RE",
                  "SSaint Barthélemy": "BL",
                  "Saint Helena Ascension and Tristan da Cunha": "SH",
                  "Saint Kitts and Nevis": "KN",
                  "Saint Lucia": "LC",
                  "Saint Martin": "MF",
                  "Saint Pierre and Miquelon": "PM",
                  "Saint Vincent and the Grenadines": "VC",
                  "Samoa": "WS",
                  "San Marino": "SM",
                  "Sao Tome and Principe": "ST",
                  "Saudi Arabia": "SA",
                  "Senegal": "SN",
                  "Serbia": "RS",
                  "Seychelles": "SC",
                  "Sierra Leone": "SL",
                  "Singapore": "SG",
                  "Sint Maarten": "SX",
                  "Slovakia": "SK",
                  "Slovenia": "SI",
                  "Solomon Islands": "SB",
                  "Somalia": "SO",
                  "South Africa": "ZA",
                  "South Georgia and the South Sandwich Islands": "GS",
                  "South Korea": "KR",
                  "South Sudan": "SS",
                  "Spain": "ES",
                  "Sri Lanka": "LK",
                  "Sudan": "SD",
                  "Suriname": "SR",
                  "Svalbard and Jan Mayen": "SJ",
                  "Swaziland": "SZ",
                  "Sweden": "SE",
                  "Switzerland": "CH",
                  "Syrian Arab Republic": "SY",
                  "Taiwan": "TW",
                  "Tajikistan": "TJ",
                  "Tanzania": "TZ",
                  "Thailand": "TH",
                  "Timor-Leste": "TL",
                  "Togo": "TG",
                  "Tokelau": "TK",
                  "Tonga": "TO",
                  "Trinidad and Tobago": "TT",
                  "Tunisia": "TN",
                  "Turkey": "TR",
                  "Turkmenistan": "TM",
                  "Turks and Caicos Islands": "TC",
                  "Tuvalu": "TV",
                  "US Virgin Islands": "VI",
                  "USA": "US",
                  "Uganda": "UG",
                  "Ukraine": "UA",
                  "United Arab Emirates": "AE",
                  "United Kingdom": "GB",
                  "United States Minor Outlying Islands": "UM",
                  "United States of America": "US",
                  "United States": "US",
                  "Uruguay": "UY",
                  "Uzbekistan": "UZ",
                  "Vanuatu": "VU",
                  "Vatican City": "VA",
                  "Venezuela": "VE",
                  "Viet Nam": "VN",
                  "Wallis and Futuna": "WF",
                  "Western Sahara": "EH",
                  "Yemen": "YE",
                  "Zambia": "ZM",
                  "Zimbabwe": "ZW"}

        #  create lowercase dictionary and reverse dictionary - iso to name
        for k, v in c_dict.items():
            self.country_dict[k.lower()] = v.lower()  # name to iso
            self.iso_dict[v.lower()] = k.lower()  # iso to name

        return False
