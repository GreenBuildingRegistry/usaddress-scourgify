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
from typing import Mapping, Union

# Local Imports
# Public Classes and Functions
from scourgify.cleaning import post_clean_addr_str
from scourgify.exceptions import (
    AddressValidationError,
    AmbiguousAddressError,
    IncompleteAddressError,
)

# Setup

# Constants

# Data Structure Definitions

# Private Functions


def _get_substrings_with_regex(string, pattern=None):
    # type: (str) -> list
    """Get substring matching regex rule.

    :param string: string to search for substring
    :type string: str
    :param pattern: regex pattern
    :type pattern: regex
    :return: str matching pattern search or None
    :rtype: list
    """
    pattern = re.compile(pattern)
    match = re.findall(pattern, string)
    return match


# Public Functions
def validate_address_components(address_dict, strict=True):
    # type: (Mapping[str, str]) -> Mapping[str, str]
    """Validate non-null values for minimally viable address elements.

    All addresses should have at least an address_line_1 and a postal_code
    or a city and state.

    :param address_dict: dict containing address components having keys
        'address_line_1', 'postal_code', 'city', 'state'
    :type address_dict: Mapping
    :param strict: bool indicating strict handling of components address parts
        city, state and postal_code, vs city and state OR postal_code
    :return: address_dict if no errors are raised.
    :rtype: Mapping
    """
    locality = (
        address_dict.get('postal_code') and
        address_dict.get('city') and address_dict.get('state')
        if strict else
        address_dict.get('postal_code') or
        (address_dict.get('city') and address_dict.get('state'))
    )
    if not address_dict.get('address_line_1'):
        msg = 'Address records must include Line 1 data.'
        raise IncompleteAddressError(msg)
    elif not locality:
        msg = (
            'Address records must contain a city, state, and postal_code.'
            if strict else
            'Address records must contain a city and state, or a postal_code'
        )
        raise IncompleteAddressError(msg)
    return address_dict


def validate_us_postal_code_format(postal_code, address):
    # type: (str, Union[str, Mapping]) -> str
    """Validate postal code conforms to US five-digit Zip or Zip+4 standards.

    :param postal_code: string containing US postal code data.
    :type postal_code: str
    :param address: dict or string containing original address.
    :type address: dict | str
    :return: original postal code if no error is raised
    :rtype: str
    """
    error = None
    msg = (
        'US Postal Codes must conform to five-digit Zip or Zip+4 standards.'
    )
    postal_code = post_clean_addr_str(postal_code)
    if '-' in postal_code:
        plus_four_code = postal_code.split('-')
        if len(plus_four_code) != 2:
            error = True
        elif len(plus_four_code[0]) != 5 or len(plus_four_code[1]) != 4:
            error = True
    elif len(postal_code) != 5:
        error = True

    if error:
        raise AddressValidationError(msg, None, address)
    else:
        return postal_code


def validate_parens_groups_parsed(line1):
    # type: (str) -> str
    """Validate any parenthesis segments have been successfully parsed.

    Assumes any parenthesis segments in original address string are either
    line 2 or ambiguous address elements.  If any parenthesis segment remains
    in line1 after all other address processing has been applied,
    AmbiguousAddressError is raised.

    :param line1: processed line1 address string portion
    :type line1: str
    :return: line1 address string
    :rtype: str
    """
    parenthesis_groups = _get_substrings_with_regex(line1, r'\((.+?)\)')
    if parenthesis_groups:
        raise AmbiguousAddressError(None, None, line1)
    else:
        return line1
