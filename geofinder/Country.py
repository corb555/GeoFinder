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

import phonetics

from geofinder import GeoDB, GeoUtil


class CnRow:
    ISO = 0
    ISO3 = 1
    NUM = 2
    LAT = 3
    LON = 4


class Country:
    def __init__(self, progress, geo_files, lang_list):
        self.logger = logging.getLogger(__name__)
        self.geo_files = geo_files
        self.progress = progress
        self.country_dict: Dict[str, str] = {}  # Dictionary of Country Name to country iso code
        self.iso_dict: Dict[str, str] = {}  # Reverse dictionary - Country ISO code to country name
        self.lang_list = lang_list

    @staticmethod
    def get_lang(country_iso:str)->str:
        res = country_lang.get(country_iso)
        if res:
            return res
        else:
            return 'en'

    def read(self) -> bool:
        """
           Read in list of country names and ISO codes
        """
        if self.progress is not None:
            self.progress.update_progress(100, "Read ISO countries...")

        # list of all countries and their ISO codes
        # This also includes some common aliases
        self.geo_files.geodb.db.begin()

        self.logger.debug(self.lang_list)

        #  Add country names to DB
        for ky, row in country_dict.items():
            # Localize country names using trans table
            for lang in self.lang_list:
                # If we have a translation table for this language, then apply it
                if trans_table.get(lang):
                    tbl = trans_table.get(lang)
                    # Look up the country translation
                    if tbl.get(ky):
                        ky = tbl.get(ky)
                    break  # Apply first translation in list

            # Create Geo_row
            # ('paris', 'fr', '07', '012', '12.345', '45.123', 'PPL')
            geo_row = [None] * GeoDB.Entry.MAX
            self.geo_files.update_geo_row_name(geo_row=geo_row, name=ky)
            geo_row[GeoDB.Entry.ISO] = row[CnRow.ISO].lower()
            geo_row[GeoDB.Entry.ADM1] = ''
            geo_row[GeoDB.Entry.ADM2] = ''
            geo_row[GeoDB.Entry.LAT] = row[CnRow.LAT]
            geo_row[GeoDB.Entry.LON] = row[CnRow.LON]
            geo_row[GeoDB.Entry.FEAT] = 'ADM0'
            geo_row[GeoDB.Entry.ID] = row[CnRow.ISO].lower()

            self.geo_files.geodb.insert(geo_row=geo_row, feat_code='ADM0')

        self.geo_files.geodb.db.commit()
        return False


country_dict = {
    'Afghanistan': ('AF', 'AFG', '4', '33', '65'),
    'Albania': ('AL', 'ALB', '8', '41', '20'),
    'Algeria': ('DZ', 'DZA', '12', '28', '3'),
    'American Samoa': ('AS', 'ASM', '16', '-14.333', '-170'),
    'Andorra': ('AD', 'AND', '20', '42.5', '1.6'),
    'Angola': ('AO', 'AGO', '24', '-12.5', '18.5'),
    'Anguilla': ('AI', 'AIA', '660', '18.25', '-63.166'),
    'Antarctica': ('AQ', 'ATA', '10', '-90', '0'),
    'Antigua and Barbuda': ('AG', 'ATG', '28', '17.05', '-61.8'),
    'Argentina': ('AR', 'ARG', '32', '-34', '-64'),
    'Armenia': ('AM', 'ARM', '51', '40', '45'),
    'Aruba': ('AW', 'ABW', '533', '12.5', '-69.966'),
    'Australia': ('AU', 'AUS', '36', '-27', '133'),
    'Austria': ('AT', 'AUT', '40', '47.333', '13.333'),
    'Azerbaijan': ('AZ', 'AZE', '31', '40.5', '47.5'),
    'Bahamas': ('BS', 'BHS', '44', '24.25', '-76'),
    'Bahrain': ('BH', 'BHR', '48', '26', '50.55'),
    'Bangladesh': ('BD', 'BGD', '50', '24', '90'),
    'Barbados': ('BB', 'BRB', '52', '13.166', '-59.533'),
    'Belarus': ('BY', 'BLR', '112', '53', '28'),
    'Belgium': ('BE', 'BEL', '56', '50.833', '4'),
    'Belize': ('BZ', 'BLZ', '84', '17.25', '-88.75'),
    'Benin': ('BJ', 'BEN', '204', '9.5', '2.25'),
    'Bermuda': ('BM', 'BMU', '60', '32.333', '-64.75'),
    'Bhutan': ('BT', 'BTN', '64', '27.5', '90.5'),
    'Bolivia, Plurinational State of': ('BO', 'BOL', '68', '-17', '-65'),
    'Bolivia': ('BO', 'BOL', '68', '-17', '-65'),
    'Bosnia and Herzegovina': ('BA', 'BIH', '70', '44', '18'),
    'Botswana': ('BW', 'BWA', '72', '-22', '24'),
    'Bouvet Island': ('BV', 'BVT', '74', '-54.433', '3.4'),
    'Brazil': ('BR', 'BRA', '76', '-10', '-55'),
    'British Indian Ocean Territory': ('IO', 'IOT', '86', '-6', '71.5'),
    'Brunei Darussalam': ('BN', 'BRN', '96', '4.5', '114.666'),
    'Brunei': ('BN', 'BRN', '96', '4.5', '114.666'),
    'Bulgaria': ('BG', 'BGR', '100', '43', '25'),
    'Burkina Faso': ('BF', 'BFA', '854', '13', '-2'),
    'Burundi': ('BI', 'BDI', '108', '-3.5', '30'),
    'Cambodia': ('KH', 'KHM', '116', '13', '105'),
    'Cameroon': ('CM', 'CMR', '120', '6', '12'),
    'Canada': ('CA', 'CAN', '124', '60', '-95'),
    'Cape Verde': ('CV', 'CPV', '132', '16', '-24'),
    'Cayman Islands': ('KY', 'CYM', '136', '19.5', '-80.5'),
    'Central African Republic': ('CF', 'CAF', '140', '7', '21'),
    'Chad': ('TD', 'TCD', '148', '15', '19'),
    'Chile': ('CL', 'CHL', '152', '-30', '-71'),
    'China': ('CN', 'CHN', '156', '35', '105'),
    'Christmas Island': ('CX', 'CXR', '162', '-10.5', '105.666'),
    'Cocos Keeling) Islands': ('CC', 'CCK', '166', '-12.5', '96.833'),
    'Colombia': ('CO', 'COL', '170', '4', '-72'),
    'Comoros': ('KM', 'COM', '174', '-12.166', '44.25'),
    'Congo': ('CG', 'COG', '178', '-1', '15'),
    'Congo, the Democratic Republic of the': ('CD', 'COD', '180', '0', '25'),
    'Cook Islands': ('CK', 'COK', '184', '-21.233', '-159.766'),
    'Costa Rica': ('CR', 'CRI', '188', '10', '-84'),
    'Côte d Ivoire': ('CI', 'CIV', '384', '8', ' - 5'),
    'Ivory Coast': ('CI', 'CIV', '384', '8', '-5'),
    'Croatia': ('HR', 'HRV', '191', '45.166', '15.5'),
    'Cuba': ('CU', 'CUB', '192', '21.5', '-80'),
    'Cyprus': ('CY', 'CYP', '196', '35', '33'),
    'Czech Republic': ('CZ', 'CZE', '203', '49.75', '15.5'),
    'Czechoslovakia': ('CZ', 'CZE', '203', '49.75', '15.5'),
    'Denmark': ('DK', 'DNK', '208', '56', '10'),
    'Djibouti': ('DJ', 'DJI', '262', '11.5', '43'),
    'Dominica': ('DM', 'DMA', '212', '15.4167', '-61.333'),
    'Dominican Republic': ('DO', 'DOM', '214', '19', '-70.666'),
    'Ecuador': ('EC', 'ECU', '218', '-2', '-77.5'),
    'Egypt': ('EG', 'EGY', '818', '27', '30'),
    'El Salvador': ('SV', 'SLV', '222', '13.833', '-88.916'),
    'Equatorial Guinea': ('GQ', 'GNQ', '226', '2', '10'),
    'Eritrea': ('ER', 'ERI', '232', '15', '39'),
    'Estonia': ('EE', 'EST', '233', '59', '26'),
    'Ethiopia': ('ET', 'ETH', '231', '8', '38'),
    'Falkland Islands Malvinas': ('FK', 'FLK', '238', '-51.75', '-59'),
    'Faroe Islands': ('FO', 'FRO', '234', '62', '-7'),
    'Fiji': ('FJ', 'FJI', '242', '-18', '175'),
    'Finland': ('FI', 'FIN', '246', '64', '26'),
    'France': ('FR', 'FRA', '250', '46', '2'),
    'French Guiana': ('GF', 'GUF', '254', '4', '-53'),
    'French Polynesia': ('PF', 'PYF', '258', '-15', '-140'),
    'French Southern Territories': ('TF', 'ATF', '260', '-43', '67'),
    'Gabon': ('GA', 'GAB', '266', '-1', '11.75'),
    'Gambia': ('GM', 'GMB', '270', '13.466', '-16.566'),
    'Georgia': ('GE', 'GEO', '268', '42', '43.5'),
    'Germany': ('DE', 'DEU', '276', '51', '9'),
    'Ghana': ('GH', 'GHA', '288', '8', '-2'),
    'Gibraltar': ('GI', 'GIB', '292', '36.183', '-5.366'),
    'Greece': ('GR', 'GRC', '300', '39', '22'),
    'Greenland': ('GL', 'GRL', '304', '72', '-40'),
    'Grenada': ('GD', 'GRD', '308', '12.116', '-61.666'),
    'Guadeloupe': ('GP', 'GLP', '312', '16.25', '-61.583'),
    'Guam': ('GU', 'GUM', '316', '13.4667', '144.783'),
    'Guatemala': ('GT', 'GTM', '320', '15.5', '-90.25'),
    'Guernsey': ('GG', 'GGY', '831', '49.5', '-2.56'),
    'Guinea': ('GN', 'GIN', '324', '11', '-10'),
    'Guinea-Bissau': ('GW', 'GNB', '624', '12', '-15'),
    'Guyana': ('GY', 'GUY', '328', '5', '-59'),
    'Haiti': ('HT', 'HTI', '332', '19', '-72.4167'),
    'Heard Island and McDonald Islands': ('HM', 'HMD', '334', '-53.1', '72.5167'),
    'Holy See': ('VA', 'VAT', '336', '41.9', '12.45'),
    'Vatican': ('VA', 'VAT', '336', '41.9', '12.45'),
    'Honduras': ('HN', 'HND', '340', '15', '-86.5'),
    'Hong Kong': ('HK', 'HKG', '344', '22.25', '114.1667'),
    'Hungary': ('HU', 'HUN', '348', '47', '20'),
    'Iceland': ('IS', 'ISL', '352', '65', '-18'),
    'India': ('IN', 'IND', '356', '20', '77'),
    'Indonesia': ('ID', 'IDN', '360', '-5', '120'),
    'Iran, Islamic Republic of': ('IR', 'IRN', '364', '32', '53'),
    'Iraq': ('IQ', 'IRQ', '368', '33', '44'),
    'Ireland': ('IE', 'IRL', '372', '53', '-8'),
    'Isle of Man': ('IM', 'IMN', '833', '54.23', '-4.55'),
    'Israel': ('IL', 'ISR', '376', '31.5', '34.75'),
    'Italy': ('IT', 'ITA', '380', '42.8333', '12.8333'),
    'Jamaica': ('JM', 'JAM', '388', '18.25', '-77.5'),
    'Japan': ('JP', 'JPN', '392', '36', '138'),
    'Jersey': ('JE', 'JEY', '832', '49.21', '-2.13'),
    'Jordan': ('JO', 'JOR', '400', '31', '36'),
    'Kazakhstan': ('KZ', 'KAZ', '398', '48', '68'),
    'Kenya': ('KE', 'KEN', '404', '1', '38'),
    'Kiribati': ('KI', 'KIR', '296', '1.4167', '173'),
    'Korea, Democratic Peoples Republic of': ('KP', 'PRK', '408', '40', '127'),
    'Korea, Republic of': ('KR', 'KOR', '410', '37', '127.5'),
    'South Korea': ('KR', 'KOR', '410', '37', '127.5'),
    'Kuwait': ('KW', 'KWT', '414', '29.3375', '47.6581'),
    'Kyrgyzstan': ('KG', 'KGZ', '417', '41', '75'),
    'Lao Peoples Democratic Republic': ('LA', 'LAO', '418', '18', '105'),
    'Latvia': ('LV', 'LVA', '428', '57', '25'),
    'Lebanon': ('LB', 'LBN', '422', '33.8333', '35.8333'),
    'Lesotho': ('LS', 'LSO', '426', '-29.5', '28.5'),
    'Liberia': ('LR', 'LBR', '430', '6.5', '-9.5'),
    'Libyan Arab Jamahiriya': ('LY', 'LBY', '434', '25', '17'),
    'Libya': ('LY', 'LBY', '434', '25', '17'),
    'Liechtenstein': ('LI', 'LIE', '438', '47.1667', '9.5333'),
    'Lithuania': ('LT', 'LTU', '440', '56', '24'),
    'Luxembourg': ('LU', 'LUX', '442', '49.75', '6.1667'),
    'Macao': ('MO', 'MAC', '446', '22.1667', '113.55'),
    'Macedonia, the former Yugoslav Republic of': ('MK', 'MKD', '807', '41.8333', '22'),
    'Madagascar': ('MG', 'MDG', '450', '-20', '47'),
    'Malawi': ('MW', 'MWI', '454', '-13.5', '34'),
    'Malaysia': ('MY', 'MYS', '458', '2.5', '112.5'),
    'Maldives': ('MV', 'MDV', '462', '3.25', '73'),
    'Mali': ('ML', 'MLI', '466', '17', '-4'),
    'Malta': ('MT', 'MLT', '470', '35.8333', '14.5833'),
    'Marshall Islands': ('MH', 'MHL', '584', '9', '168'),
    'Martinique': ('MQ', 'MTQ', '474', '14.6667', '-61'),
    'Mauritania': ('MR', 'MRT', '478', '20', '-12'),
    'Mauritius': ('MU', 'MUS', '480', '-20.2833', '57.55'),
    'Mayotte': ('YT', 'MYT', '175', '-12.8333', '45.1667'),
    'Mexico': ('MX', 'MEX', '484', '23', '-102'),
    'Micronesia, Federated States of': ('FM', 'FSM', '583', '6.9167', '158.25'),
    'Moldova, Republic of': ('MD', 'MDA', '498', '47', '29'),
    'Monaco': ('MC', 'MCO', '492', '43.7333', '7.4'),
    'Mongolia': ('MN', 'MNG', '496', '46', '105'),
    'Montenegro': ('ME', 'MNE', '499', '42', '19'),
    'Montserrat': ('MS', 'MSR', '500', '16.75', '-62.2'),
    'Morocco': ('MA', 'MAR', '504', '32', '-5'),
    'Mozambique': ('MZ', 'MOZ', '508', '-18.25', '35'),
    'Myanmar': ('MM', 'MMR', '104', '22', '98'),
    'Burma': ('MM', 'MMR', '104', '22', '98'),
    'Namibia': ('NA', 'NAM', '516', '-22', '17'),
    'Nauru': ('NR', 'NRU', '520', '-0.5333', '166.9167'),
    'Nepal': ('NP', 'NPL', '524', '28', '84'),
    'Netherlands': ('NL', 'NLD', '528', '52.5', '5.75'),
    'Netherlands Antilles': ('AN', 'ANT', '530', '12.25', '-68.75'),
    'New Caledonia': ('NC', 'NCL', '540', '-21.5', '165.5'),
    'New Zealand': ('NZ', 'NZL', '554', '-41', '174'),
    'Nicaragua': ('NI', 'NIC', '558', '13', '-85'),
    'Niger': ('NE', 'NER', '562', '16', '8'),
    'Nigeria': ('NG', 'NGA', '566', '10', '8'),
    'Niue': ('NU', 'NIU', '570', '-19.0333', '-169.8667'),
    'Norfolk Island': ('NF', 'NFK', '574', '-29.0333', '167.95'),
    'Northern Mariana Islands': ('MP', 'MNP', '580', '15.2', '145.75'),
    'Norway': ('NO', 'NOR', '578', '62', '10'),
    'Oman': ('OM', 'OMN', '512', '21', '57'),
    'Pakistan': ('PK', 'PAK', '586', '30', '70'),
    'Palau': ('PW', 'PLW', '585', '7.5', '134.5'),
    'Palestinian Territory, Occupied': ('PS', 'PSE', '275', '32', '35.25'),
    'Panama': ('PA', 'PAN', '591', '9', '-80'),
    'Papua New Guinea': ('PG', 'PNG', '598', '-6', '147'),
    'Paraguay': ('PY', 'PRY', '600', '-23', '-58'),
    'Peru': ('PE', 'PER', '604', '-10', '-76'),
    'Philippines': ('PH', 'PHL', '608', '13', '122'),
    'Pitcairn': ('PN', 'PCN', '612', '-24.7', '-127.4'),
    'Poland': ('PL', 'POL', '616', '52', '20'),
    'Portugal': ('PT', 'PRT', '620', '39.5', '-8'),
    'Puerto Rico': ('PR', 'PRI', '630', '18.25', '-66.5'),
    'Qatar': ('QA', 'QAT', '634', '25.5', '51.25'),
    'Réunion': ('RE', 'REU', '638', '-21.1', '55.6'),
    'Romania': ('RO', 'ROU', '642', '46', '25'),
    'Russia': ('RU', 'RUS', '643', '60', '100'),
    'Rwanda': ('RW', 'RWA', '646', '-2', '30'),
    'Saint Helena, Ascension and Tristan da Cunha': ('SH', 'SHN', '654', '-15.9333', '-5.7'),
    'Saint Kitts and Nevis': ('KN', 'KNA', '659', '17.3333', '-62.75'),
    'Saint Lucia': ('LC', 'LCA', '662', '13.8833', '-61.1333'),
    'Saint Pierre and Miquelon': ('PM', 'SPM', '666', '46.8333', '-56.3333'),
    'Saint Vincent and the Grenadines': ('VC', 'VCT', '670', '13.25', '-61.2'),
    'Samoa': ('WS', 'WSM', '882', '-13.5833', '-172.3333'),
    'San Marino': ('SM', 'SMR', '674', '43.7667', '12.4167'),
    'Sao Tome and Principe': ('ST', 'STP', '678', '1', '7'),
    'Saudi Arabia': ('SA', 'SAU', '682', '25', '45'),
    'Senegal': ('SN', 'SEN', '686', '14', '-14'),
    'Serbia': ('RS', 'SRB', '688', '44', '21'),
    'Seychelles': ('SC', 'SYC', '690', '-4.5833', '55.6667'),
    'Sierra Leone': ('SL', 'SLE', '694', '8.5', '-11.5'),
    'Singapore': ('SG', 'SGP', '702', '1.3667', '103.8'),
    'Slovakia': ('SK', 'SVK', '703', '48.6667', '19.5'),
    'Slovenia': ('SI', 'SVN', '705', '46', '15'),
    'Solomon Islands': ('SB', 'SLB', '90', '-8', '159'),
    'Somalia': ('SO', 'SOM', '706', '10', '49'),
    'South Africa': ('ZA', 'ZAF', '710', '-29', '24'),
    'South Georgia and the South Sandwich Islands': ('GS', 'SGS', '239', '-54.5', '-37'),
    'Spain': ('ES', 'ESP', '724', '40', '-4'),
    'Sri Lanka': ('LK', 'LKA', '144', '7', '81'),
    'Sudan': ('SD', 'SDN', '736', '15', '30'),
    'Suriname': ('SR', 'SUR', '740', '4', '-56'),
    'Svalbard and Jan Mayen': ('SJ', 'SJM', '744', '78', '20'),
    'Swaziland': ('SZ', 'SWZ', '748', '-26.5', '31.5'),
    'Sweden': ('SE', 'SWE', '752', '62', '15'),
    'Switzerland': ('CH', 'CHE', '756', '47', '8'),
    'Syrian Arab Republic': ('SY', 'SYR', '760', '35', '38'),
    'Taiwan, Province of China': ('TW', 'TWN', '158', '23.5', '121'),
    'Taiwan': ('TW', 'TWN', '158', '23.5', '121'),
    'Tajikistan': ('TJ', 'TJK', '762', '39', '71'),
    'Tanzania, United Republic of': ('TZ', 'TZA', '834', '-6', '35'),
    'Thailand': ('TH', 'THA', '764', '15', '100'),
    'Timor-Leste': ('TL', 'TLS', '626', '-8.55', '125.5167'),
    'Togo': ('TG', 'TGO', '768', '8', '1.1667'),
    'Tokelau': ('TK', 'TKL', '772', '-9', '-172'),
    'Tonga': ('TO', 'TON', '776', '-20', '-175'),
    'Trinidad and Tobago': ('TT', 'TTO', '780', '11', '-61'),
    'Tunisia': ('TN', 'TUN', '788', '34', '9'),
    'Turkey': ('TR', 'TUR', '792', '39', '35'),
    'Turkmenistan': ('TM', 'TKM', '795', '40', '60'),
    'Turks and Caicos Islands': ('TC', 'TCA', '796', '21.75', '-71.5833'),
    'Tuvalu': ('TV', 'TUV', '798', '-8', '178'),
    'Uganda': ('UG', 'UGA', '800', '1', '32'),
    'Ukraine': ('UA', 'UKR', '804', '49', '32'),
    'United Arab Emirates': ('AE', 'ARE', '784', '24', '54'),
    'United Kingdom': ('GB', 'GBR', '826', '54', '-2'),
    'United States': ('US', 'USA', '840', '38', '-97'),
    'U.S.A.': ('US', 'USA', '840', '38', '-97'),
    'USA': ('US', 'USA', '840', '38', '-97'),
    'United States of America': ('US', 'USA', '840', '38', '-97'),
    'United States Minor Outlying Islands': ('UM', 'UMI', '581', '19.2833', '166.6'),
    'Uruguay': ('UY', 'URY', '858', '-33', '-56'),
    'Uzbekistan': ('UZ', 'UZB', '860', '41', '64'),
    'Vanuatu': ('VU', 'VUT', '548', '-16', '167'),
    'Venezuela, Bolivarian Republic of': ('VE', 'VEN', '862', '8', '-66'),
    'Venezuela': ('VE', 'VEN', '862', '8', '-66'),
    'Vietnam': ('VN', 'VNM', '704', '16', '106'),
    'Virgin Islands, British': ('VG', 'VGB', '92', '18.5', '-64.5'),
    'Virgin Islands, U.S.': ('VI', 'VIR', '850', '18.3333', '-64.8333'),
    'Wallis and Futuna': ('WF', 'WLF', '876', '-13.3', '-176.2'),
    'Western Sahara': ('EH', 'ESH', '732', '24.5', '-13'),
    'Yemen': ('YE', 'YEM', '887', '15', '48'),
    'Zambia': ('ZM', 'ZMB', '894', '-15', '30'),
    'Zimbabwe': ('ZW', 'ZWE', '716', '-20', '30')
}


# Country code to Lang
country_lang = {
"AF"  :   "ps",
"AL"  :   "sq",
"DZ"  :   "ar",
"AR"  :   "es",
"AM"  :   "hy",
"AU"  :   "en",
"AT"  :   "de",
"AZ"  :   "az",
"BH"  :   "ar",
"BD"  :   "bn",
"BY"  :   "be",
"BE"  :   "fr",
"BZ"  :   "en",
"VE"  :   "es",
"BO"  :   "es",
"BR"  :   "pt",
"BN"  :   "ms",
"BG"  :   "bg",
"KH"  :   "km",
"CA"  :   "en",
"CL"  :   "es",
"CO"  :   "es",
"CR"  :   "es",
"HR"  :   "hr",
"CZ"  :   "cs",
"DK"  :   "da",
"DO"  :   "es",
"EC"  :   "es",
"EG"  :   "ar",
"SV"  :   "es",
"EE"  :   "et",
"ET"  :   "am",
"FO"  :   "fo",
"FI"  :   "fi",
"FR"  :   "fr",
"GE"  :   "ka",
"DE"  :   "de",
"GR"  :   "el",
"GL"  :   "kl",
"GT"  :   "es",
"HN"  :   "es",
"HU"  :   "hu",
"IS"  :   "is",
"ID"  :   "id",
"IR"  :   "fa",
"IE"  :   "en",
"PK"  :   "ur",
"IL"  :   "he",
"IT"  :   "it",
"JM"  :   "en",
"JP"  :   "ja",
"JO"  :   "ar",
"KZ"  :   "kk",
"KE"  :   "sw",
"KR"  :   "ko",
"KW"  :   "ar",
"KG"  :   "ky",
"LA"  :   "lo",
"LV"  :   "lv",
"LB"  :   "ar",
"LY"  :   "ar",
"LI"  :   "de",
"LT"  :   "lt",
"LU"  :   "fr",
"MO"  :   "zh",
"MK"  :   "mk",
"MY"  :   "ms",
"MV"  :   "dv",
"MT"  :   "mt",
"MX"  :   "es",
"MN"  :   "mn",
"ME"  :   "sr",
"MA"  :   "ar",
"NP"  :   "ne",
"NL"  :   "nl",
"NZ"  :   "en",
"NI"  :   "es",
"NG"  :   "yo",
"NO"  :   "nn",
"OM"  :   "ar",
"PA"  :   "es",
"PY"  :   "es",
"CN"  :   "zh",
"PE"  :   "es",
"PL"  :   "pl",
"PT"  :   "pt",
"MC"  :   "fr",
"PR"  :   "es",
"QA"  :   "ar",
"PH"  :   "en",
"RO"  :   "ro",
"RU"  :   "ru",
"RW"  :   "rw",
"SA"  :   "ar",
"SN"  :   "wo",
"RS"  :   "sr",
"SG"  :   "en",
"SK"  :   "sk",
"SI"  :   "sl",
"ES"  :   "es",
"LK"  :   "si",
"SE"  :   "sv",
"CH"  :   "de",
"TW"  :   "zh",
"TJ"  :   "tg",
"TH"  :   "th",
"TT"  :   "en",
"TN"  :   "ar",
"TR"  :   "tr",
"TM"  :   "tk",
"AE"  :   "ar",
"UA"  :   "uk",
"GB"  :   "en",
"US"  :   "en",
"UY"  :   "es",
"UZ"  :   "uz",
"VN"  :   "vi",
"YE"  :   "ar",
"ZW"  :   "en",
}


# Non English Country Name tables

# Dutch
nl_trans = {
    "Afghanistan": "Afghanistan",
    "Albania": "Albanië",
    "Algeria": "Algerije",
    "Andorra": "Andorra",
    "Angola": "Angola",
    "Antigua and Barbuda": "Antigua en Barbuda",
    "Argentina": "Argentinië",
    "Armenia": "Armenië",
    "Australia": "Australië",
    "Austria": "Oostenrijk",
    "Azerbaijan": "Azerbeidzjan",
    "Bahamas": "Bahama’s",
    "Bahrain": "Bahrein",
    "Bangladesh": "Bangladesh",
    "Barbados": "Barbados",
    "Belarus": "Wit-Rusland",
    "Belgium": "België",
    "Belize": "Belize",
    "Benin": "Benin",
    "Bhutan": "Bhutan",
    "Bolivia": "Bolivia",
    "Bosnia and Herzegovina": "Bosnië en Herzegovina",
    "Botswana": "Botswana",
    "Brazil": "Brazilië",
    "Brunei": "Brunei",
    "Bulgaria": "Bulgarije",
    "Burkina Faso": "Burkina Faso",
    "Burundi": "Burundi",
    "Cambodia": "Cambodja",
    "Cameroon": "Kameroen",
    "Canada": "Canada",
    "Cape Verde": "Kaapverdië",
    "Central African Republic": "Centraal-Afrikaanse Republiek",
    "Chad": "Tsjaad",
    "Chile": "Chili",
    "China": "China",
    "Colombia": "Colombia",
    "Comoros": "Comoren",
    "Costa Rica": "Costa Rica",
    "Côte d’Ivoire": "Ivoorkust",
    "Croatia": "Kroatië",
    "Cuba": "Cuba",
    "Cyprus": "Cyprus",
    "Czech Republic": "Tsjechië",
    "Democratic Republic of the Congo": "Democratische Republiek Congo",
    "Denmark": "Denemarken",
    "Djibouti": "Djibouti",
    "Dominica": "Dominica",
    "Dominican Republic": "Dominicaanse Republiek",
    "East Timor": "Oost-Timor",
    "Ecuador": "Ecuador",
    "Egypt": "Egypte",
    "El Salvador": "El Salvador",
    "Equatorial Guinea": "Equatoriaal-Guinea",
    "Eritrea": "Eritrea",
    "Estonia": "Estland",
    "Ethiopia": "Ethiopië",
    "Fiji": "Fiji",
    "Finland": "Finland",
    "France": "Frankrijk",
    "Gabon": "Gabon",
    "Gambia": "Gambia",
    "Georgia": "Georgië",
    "Germany": "Duitsland",
    "Ghana": "Ghana",
    "Greece": "Griekenland",
    "Grenada": "Grenada",
    "Guatemala": "Guatemala",
    "Guinea": "Guinea",
    "Guinea-Bissau": "Guinee-Bissau",
    "Guyana": "Guyana",
    "Haiti": "Haïti",
    "Honduras": "Honduras",
    "Hungary": "Hongarije",
    "Iceland": "IJsland",
    "India": "Indië",
    "Indonesia": "Indonesië",
    "Iran": "Iran",
    "Iraq": "Irak",
    "Ireland": "Ierland",
    "Israel": "Israël",
    "Italy": "Italië",
    "Jamaica": "Jamaica",
    "Japan": "Japan",
    "Jordan": "Jordanië",
    "Kazakhstan": "Kazachstan",
    "Kenya": "Kenia",
    "Kiribati": "Kiribati",
    "Kuwait": "Koeweit",
    "Kyrgyzstan": "Kirgizië",
    "Laos": "Laos",
    "Latvia": "Letland",
    "Lebanon": "Libanon",
    "Lesotho": "Lesotho",
    "Liberia": "Liberia",
    "Libya": "Libië",
    "Liechtenstein": "Liechtenstein",
    "Lithuania": "Litouwen",
    "Luxembourg": "Luxemburg",
    "Madagascar": "Madagaskar",
    "Malawi": "Malawi",
    "Malaysia": "Maleisië",
    "Maldives": "Maldiven",
    "Mali": "Mali",
    "Malta": "Malta",
    "Marshall Islands": "Marshalleilanden",
    "Mauritania": "Mauritanië",
    "Mauritius": "Mauritius",
    "Mexico": "Mexico",
    "Micronesia": "Micronesië",
    "Moldova": "Moldavië",
    "Monaco": "Monaco",
    "Mongolia": "Mongolië",
    "Montenegro": "Montenegro",
    "Morocco": "Marokko",
    "Mozambique": "Mozambique",
    "Myanmar": "Myanmar",
    "Namibia": "Namibië",
    "Nauru": "Nauru",
    "Nepal": "Nepal",
    "Netherlands": "Nederland",
    "New Zealand": "Nieuw-Zeeland",
    "Nicaragua": "Nicaragua",
    "Niger": "Niger",
    "Nigeria": "Nigeria",
    "North Korea": "Noord-Korea",
    "Norway": "Noorwegen",
    "Oman": "Oman",
    "Pakistan": "Pakistan",
    "Palau": "Palau",
    "Panama": "Panama",
    "Papua New Guinea": "Papoea-Nieuw-Guinea",
    "Paraguay": "Paraguay",
    "Peru": "Peru",
    "Philippines": "Filipijnen",
    "Poland": "Polen",
    "Portugal": "Portugal",
    "Qatar": "Qatar",
    "Republic of the Congo": "Republiek Congo",
    "Republic of Macedonia": "Macedonië",
    "Romania": "Roemenië",
    "Russia": "Rusland",
    "Rwanda": "Rwanda",
    "Saint Kitts and Nevis": "Saint Kitts en Nevis",
    "Saint Lucia": "Saint Lucia",
    "Saint Vincent and the Grenadines": "Saint Vincent en de Grenadines",
    "Samoa": "Samoa",
    "San Marino": "San Marino",
    "Sao Tome and Principe": "Sao Tomé en Principe",
    "Saudi Arabia": "Saoedi-Arabië",
    "Senegal": "Senegal",
    "Serbia": "Servië",
    "Seychelles": "Seychellen",
    "Sierra Leone": "Sierra Leone",
    "Singapore": "Singapore",
    "Slovakia": "Slowakije",
    "Slovenia": "Slovenië",
    "Solomon Islands": "Salomonseilanden",
    "Somalia": "Somalië",
    "South Africa": "Zuid-Afrika",
    "South Korea": "Zuid-Korea",
    "South Sudan": "Zuid-Soedan",
    "Spain": "Spanje",
    "Sri Lanka": "Sri Lanka",
    "Sudan": "Soedan",
    "Suriname": "Suriname",
    "Swaziland": "Swaziland",
    "Sweden": "Zweden",
    "Switzerland": "Zwitserland",
    "Syria": "Syrië",
    "Tajikistan": "Tadzjikistan",
    "Tanzania": "Tanzania",
    "Thailand": "Thailand",
    "Togo": "Togo",
    "Tonga": "Tonga",
    "Trinidad and Tobago": "Trinidad en Tobago",
    "Tunisia": "Tunesië",
    "Turkey": "Turkije",
    "Turkmenistan": "Turkmenistan",
    "Tuvalu": "Tuvalu",
    "Uganda": "Oeganda",
    "Ukraine": "Oekraïne",
    "United Arab Emirates": "Verenigde Arabische Emiraten",
    "United Kingdom": "Verenigd Koninkrijk",
    "United States of America": "Verenigde Staten",
    "USA": "Verenigde Staten",
    "United States": "Verenigde Staten",
    "Uruguay": "Uruguay",
    "Uzbekistan": "Oezbekistan",
    "Vanuatu": "Vanuatu",
    "Venezuela": "Venezuela",
    "Vietnam": "Vietnam",
    "Yemen": "Jemen",
    "Zambia": "Zambia",
    "Zimbabwe": "Zimbabwe",
}


# German
de_trans = {
    "Afghanistan": "Afghanistan",
    "Albania": "Albanien",
    "Algeria": "Algerien",
    "Andorra": "Andorra",
    "Angola": "Angola",
    "Antigua and Barbuda": "Antigua und Barbuda",
    "Argentina": "Argentinien",
    "Armenia": "Armenien",
    "Australia": "Australien",
    "Austria": "Österreich",
    "Azerbaijan": "Aserbaidschan",
    "Bahamas": "Bahamas",
    "Bahrain": "Bahrain",
    "Bangladesh": "Bangladesch",
    "Barbados": "Barbados",
    "Belarus": "Weißrussland",
    "Belgium": "Belgien",
    "Belize": "Belize",
    "Benin": "Benin",
    "Bhutan": "Bhutan",
    "Bolivia": "Bolivien",
    "Bosnia and Herzegovina": "Bosnien und Herzegowina",
    "Botswana": "Botswana",
    "Brazil": "Brasilien",
    "Brunei": "Brunei",
    "Bulgaria": "Bulgarien",
    "Burkina Faso": "Burkina Faso",
    "Burundi": "Burundi",
    "Cambodia": "Kambodscha",
    "Cameroon": "Kamerun",
    "Canada": "Kanada",
    "Cape Verde": "Kap Verde",
    "Central African Republic": "Zentralafrikanische Republik",
    "Chad": "Tschad",
    "Chile": "Chile",
    "China": "China",
    "Colombia": "Kolumbien",
    "Comoros": "Komoren",
    "Costa Rica": "Costa Rica",
    "Côte d’Ivoire": "Elfenbeinküste",
    "Croatia": "Kroatien",
    "Cuba": "Kuba",
    "Cyprus": "Zypern",
    "Czech Republic": "Tschechien",
    "Democratic Republic of the Congo": "Demokratische Republik Kongo",
    "Denmark": "Dänemark",
    "Djibouti": "Dschibuti",
    "Dominica": "Dominica",
    "Dominican Republic": "Dominikanische Republik",
    "East Timor": "Osttimor",
    "Ecuador": "Ecuador",
    "Egypt": "Ägypten",
    "El Salvador": "El Salvador",
    "Equatorial Guinea": "Äquatorialguinea",
    "Eritrea": "Eritrea",
    "Estonia": "Estland",
    "Ethiopia": "Äthiopien",
    "Fiji": "Fidschi",
    "Finland": "Finnland",
    "France": "Frankreich",
    "Gabon": "Gabun",
    "Gambia": "Gambia",
    "Georgia": "Georgia",
    "Germany": "Deutschland",
    "Ghana": "Ghana",
    "Greece": "Griechenland",
    "Grenada": "Grenada",
    "Guatemala": "Guatemala",
    "Guinea": "Guinea",
    "Guinea-Bissau": "Guinea-Bissau",
    "Guyana": "Guyana",
    "Haiti": "Haiti",
    "Honduras": "Honduras",
    "Hungary": "Ungarn",
    "Iceland": "Island",
    "India": "Indien",
    "Indonesia": "Indonesien",
    "Iran": "Iran",
    "Iraq": "Irak",
    "Ireland": "Irland",
    "Israel": "Israel",
    "Italy": "Italien",
    "Jamaica": "Jamaika",
    "Japan": "Japan",
    "Jordan": "Jordan",
    "Kazakhstan": "Kasachstan",
    "Kenya": "Kenia",
    "Kiribati": "Kiribati",
    "Kuwait": "Kuwait",
    "Kyrgyzstan": "Kirgisistan",
    "Laos": "Laos",
    "Latvia": "Lettland",
    "Lebanon": "Libanon",
    "Lesotho": "Lesotho",
    "Liberia": "Liberia",
    "Libya": "Libyen",
    "Liechtenstein": "Liechtenstein",
    "Lithuania": "Litauen",
    "Luxembourg": "Luxemburg",
    "Madagascar": "Madagaskar",
    "Malawi": "Malawi",
    "Malaysia": "Malaysia",
    "Maldives": "Malediven",
    "Mali": "Mali",
    "Malta": "Malta",
    "Marshall Islands": "Marshallinseln",
    "Mauritania": "Mauretanien",
    "Mauritius": "Mauritius",
    "Mexico": "Mexiko",
    "Micronesia": "Mikronesien",
    "Moldova": "Moldawien",
    "Monaco": "Monaco",
    "Mongolia": "Mongolei",
    "Montenegro": "Montenegro",
    "Morocco": "Marokko",
    "Mozambique": "Mosambik",
    "Myanmar": "Myanmar",
    "Namibia": "Namibia",
    "Nauru": "Nauru",
    "Nepal": "Nepal",
    "Netherlands": "Niederlande",
    "New Zealand": "Neuseeland",
    "Nicaragua": "Nicaragua",
    "Niger": "Niger",
    "Nigeria": "Nigeria",
    "North Korea": "Nordkorea",
    "Norway": "Norwegen",
    "Oman": "Oman",
    "Pakistan": "Pakistan",
    "Palau": "Palau",
    "Panama": "Panama",
    "Papua New Guinea": "Papua-Neuguinea",
    "Paraguay": "Paraguay",
    "Peru": "Peru",
    "Philippines": "Philippinen",
    "Poland": "Polen",
    "Portugal": "Portugal",
    "Qatar": "Katar",
    "Republic of the Congo": "Republik Kongo",
    "Republic of Macedonia": "Mazedonien",
    "Romania": "Rumänien",
    "Russia": "Russland",
    "Rwanda": "Ruanda",
    "Saint Kitts and Nevis": "St. Kitts und Nevis",
    "Saint Lucia": "St. Lucia",
    "Saint Vincent and the Grenadines": "St. Vincent und die Grenadinen",
    "Samoa": "Samoa",
    "San Marino": "San Marino",
    "Sao Tome and Principe": "São Tomé und Príncipe",
    "Saudi Arabia": "Saudi-Arabien",
    "Senegal": "Senegal",
    "Serbia": "Serbien",
    "Seychelles": "Seychellen",
    "Sierra Leone": "Sierra Leone",
    "Singapore": "Singapur",
    "Slovakia": "Slowakei",
    "Slovenia": "Slowenien",
    "Solomon Islands": "Salomonen",
    "Somalia": "Somalia",
    "South Africa": "Südafrika",
    "South Korea": "Südkorea",
    "South Sudan": "Südsudan",
    "Spain": "Spanien",
    "Sri Lanka": "Sri Lanka",
    "Sudan": "Sudan",
    "Suriname": "Suriname",
    "Swaziland": "Swasiland",
    "Sweden": "Schweden",
    "Switzerland": "Schweiz",
    "Syria": "Syrien",
    "Tajikistan": "Tadschikistan",
    "Tanzania": "Tansania",
    "Thailand": "Thailand",
    "Togo": "Togo",
    "Tonga": "Tonga",
    "Trinidad and Tobago": "Trinidad und Tobago Tobago",
    "Tunisia": "Tunesien",
    "Turkey": "Türkei",
    "Turkmenistan": "Turkmenistan",
    "Tuvalu": "Tuvalu",
    "Uganda": "Uganda",
    "Ukraine": "Ukraine",
    "United Arab Emirates": "Vereinigte Arabische Emirate Emirate",
    "United Kingdom": "Königreich Großbritannien",
    "United States of America": "Vereinigte Staaten",
    "USA": "Vereinigte Staaten",
    "United States": "Vereinigte Staaten",
    "Uruguay": "Uruguay",
    "Uzbekistan": "Usbekistan",
    "Vanuatu": "Vanuatu",
    "Venezuela": "Venezuela",
    "Vietnam": "Vietnam",
    "Yemen": "Jemen",
    "Zambia": "Sambia",
    "Zimbabwe": "Simbabwe",

}

trans_table = {
    'nl': nl_trans,
    #'de': de_trans,
}
