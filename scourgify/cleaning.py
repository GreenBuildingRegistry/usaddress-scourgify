#!/usr/bin/env python
# encoding: utf-8
"""
copyright (c) 2016-2017 Earth Advantage.
All rights reserved
..codeauthor::Fable Turas <fable@rainsoftware.tech>

[ INSERT DOC STRING ]  # TODO
"""

# Imports from Standard Library
import re
import unicodedata
from typing import Any, Optional, Sequence, Union

# Imports from Third Party Modules
import usaddress

# Local Imports
from scourgify.address_constants import (
    KNOWN_ODDITIES,
    OCCUPANCY_TYPE_ABBREVIATIONS,
    PROBLEM_ST_TYPE_ABBRVS,
)

# Setup

# Constants
# periods (in decimals), hyphens, / , and & are acceptable address components
# ord('&') ord('#') ord('-'), ord('.') and ord('/')
ALLOWED_CHARS = [35, 38, 45, 46, 47]

# Don't remove ',', '(' or ')' in PRE_CLEAN
PRECLEAN_EXCLUDE = [40, 41, 44]
EXCLUDE_ALL = ALLOWED_CHARS + PRECLEAN_EXCLUDE

STRIP_CHAR_CATS = (
    'M', 'S', 'C', 'Nl', 'No', 'Pc', 'Ps', 'Pe', 'Pi', 'Pf', 'Po'
)
STRIP_PUNC_CATS = ('Z', 'Pd')
STRIP_ALL_CATS = STRIP_CHAR_CATS + STRIP_PUNC_CATS

# Data Structure Definitions

# Private Functions


# Public Classes and Functions

def pre_clean_addr_str(addr_str, state=None):
    # type: (str, Optional[str]) -> str
    """Remove any known undesirable sub-strings and special characters.

    Cleaning should be enacted on an addr_str to remove known characters
    and phrases that might prevent usaddress from successfully parsing.
    Follows USPS pub 28 guidelines for undesirable special characters.
    Non-address phrases or character sets known to occur in raw addresses
    should be added to address_constants.KNOWN_ODDITIES.

    Some characters are left behind to potentially assist in second chance
    processing of unparseable addresses and should be further cleaned
    post_processing. (see post_clean_addr_str).

    :param addr_str: raw address string
    :type addr_str: str
    :param state: optional string containing normalized state data.
    :type state: str
    :return: cleaned string
    :rtype: str
    """
    # replace any easily handled, undesirable sub-strings
    if any(oddity in addr_str for oddity in KNOWN_ODDITIES.keys()):
        for key, replacement in KNOWN_ODDITIES.items():      # pragma: no cover
            addr_str = addr_str.replace(key, replacement)

    # remove non-decimal point period chars.
    if '.' in addr_str:                                      # pragma: no cover
        addr_str = clean_period_char(addr_str)

    # remove special characters per USPS pub 28, except & which impacts
    # intersection addresses, and - which impacts range addresses and zipcodes.
    # ',', '(' and ')' are also left for potential use in additional line 2
    # processing functions
    addr_str = clean_upper(
        addr_str, exclude=EXCLUDE_ALL, removal_cats=STRIP_CHAR_CATS
    )

    # to prevent any potential confusion between CT = COURT v CT = Connecticut,
    # clean_ambiguous_street_types is not applied if state is CT.
    if state and state != 'CT':
        addr_str = clean_ambiguous_street_types(addr_str)

    return addr_str


def clean_ambiguous_street_types(addr_str):
    # type: (str) -> str
    """Clean street type abbreviations treated ambiguously by usaddress.

    Some two char street type abbreviations (ie. CT) are treated as StateName
    by usaddress when address lines are parsed in isolation. To correct this,
    known problem abbreviations are converted to their whole word equivalent.

    :param addr_str: string containing address street and occupancy data
        without city and state.
    :type addr_str: str | None
    :return: original or cleaned addr_str
    :rtype: str | None
    """
    if addr_str:
        split_addr = addr_str.split()
        for key in PROBLEM_ST_TYPE_ABBRVS:
            if key in split_addr:
                split_addr[split_addr.index(key)] = PROBLEM_ST_TYPE_ABBRVS[key]
                addr_str = ' '.join(split_addr)
                break
    return addr_str


def post_clean_addr_str(addr_str):
    # type: (Union[str, None], Optional[bool]) -> str
    """Remove any special chars or extra white space remaining post-processing.

    :param addr_str: post-processing address string.
    :type addr_str: str | None
    :param is_line2: optional boolean to trigger extra line 2 processing.
    :type is_line2: bool
    :return: str set to uppercase, extra white space and special chars removed.
    :rtype: str
    """
    if addr_str:
        addr_str = clean_upper(
            addr_str, exclude=ALLOWED_CHARS, removal_cats=STRIP_CHAR_CATS
        )
    return addr_str


def _parse_occupancy(addr_line_2):
    occupancy = None
    if addr_line_2:
        parsed = None
        # first try usaddress parsing labels
        try:
            parsed = usaddress.tag(addr_line_2)
        except usaddress.RepeatedLabelError:
            pass
        if parsed:
            occupancy = parsed[0].get('OccupancyIdentifier')
    return occupancy


def strip_occupancy_type(addr_line_2):
    # type: (str) -> str
    """Strip occupancy type (ie apt, unit, etc) from addr_line_2 string

    :param addr_line_2: address line 2 string that may contain type
    :type addr_line_2: str
    :return:
    :rtype: str
    """
    occupancy = None
    if addr_line_2:
        addr_line_2 = addr_line_2.replace('#', '').strip().upper()
        occupancy = _parse_occupancy(addr_line_2)

        # if that doesn't work, clean abbrevs and try again
        if not occupancy:
            parts = str(addr_line_2).split()
            for p in parts:
                if p in OCCUPANCY_TYPE_ABBREVIATIONS:
                    addr_line_2 = addr_line_2.replace(
                        p, OCCUPANCY_TYPE_ABBREVIATIONS[p]
                    )
            occupancy = _parse_occupancy(addr_line_2)

            # if that doesn't work, dissect it manually
            if not occupancy:
                occupancy = addr_line_2
                types = (
                    list(OCCUPANCY_TYPE_ABBREVIATIONS.keys())
                    + list(OCCUPANCY_TYPE_ABBREVIATIONS.values())
                )
                if parts and len(parts) > 1:
                    ids = [p for p in parts if p not in types]
                    print(ids)
                    occupancy = ' '.join(ids)

    return occupancy


def clean_upper(text,                           # type: Any
                exclude=None,                   # type: Optional[Sequence[int]]
                removal_cats=STRIP_CHAR_CATS,   # type: Optional[Sequence[str]]
                strip_spaces=False              # type: Optional[bool]
                ):
    # type: (str, Optional[Sequence[int]], Optional[Sequence[str]]) -> str
    """
    Return text as upper case unicode string and remove unwanted characters.
    Defaults to STRIP_CHARS e.g all  whitespace, punctuation etc
    :param text: text to clean
    :type text: str
    :param exclude: sequence of char ordinals to exclude from text.translate
    :type exclude: Sequence
    :param removal_cats: sequence of strings identifying unicodedata categories
        (or startswith) of characters to be removed from text
    :type removal_cats: Sequence
    :param strip_spaces: Bool to indicate whether to leave or remove all
        spaces. Default is False (leaves single spaces)
    :type strip_spaces: bool
    :return: cleaned uppercase unicode string
    :rtype: str
    """
    exclude = exclude or []
    # coerce ints etc to str
    if not isinstance(text, str):  # pragma: no cover
        text = str(text)
    # catch and convert fractions
    text = unicodedata.normalize('NFKD', text)
    text = text.translate({8260: '/'})

    # evaluate string without commas (,) or ampersand (&) to determine if
    # further processing is necessary
    alnum_text = text.translate({44: None, 38: None})

    # remove unwanted non-alphanumeric characters and convert all dash type
    # characters to hyphen
    if not alnum_text.replace(' ', '').isalnum():
        for char in text:
            if (unicodedata.category(char).startswith(removal_cats)
                    and ord(char) not in exclude):
                text = text.translate({ord(char): None})
            elif unicodedata.category(char).startswith('Pd'):
                text = text.translate({ord(char): '-'})
    join_char = ' '
    if strip_spaces:
        join_char = ''
    # remove extra spaces and convert to uppercase
    return join_char.join(text.split()).upper()


def clean_period_char(text):
    """Remove all period characters that are not decimal points.

    :param text: string text to clean
    :type text: str
    :return: cleaned string
    :rtype: str
    """
    period_pattern = re.compile(r'\.(?!\d)')
    return re.sub(period_pattern, '', text)
