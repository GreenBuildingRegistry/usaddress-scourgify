#!/usr/bin/env python
# encoding: utf-8
"""
copyright (c) 2016  Earth Advantage.
All rights reserved
..codeauthor::Fable Turas <fable@rainsoftware.tech>

Provides functions to normalize address per USPS pub 28 and/or RESO standards.
"""
# TODO: Find why # with no street gets through
# form_normalization = {
#     'jurisdiction_property_id': 'TST123',
#     'address_line_1': '123',
#     'city': 'Portland',
#     'state': 'OR',
#     'postal_code': '97212'
# }

# Imports from Standard Library

from string import Template
from collections import OrderedDict  # noqa # pylint: disable=unused-import
from typing import (  # noqa # pylint: disable=unused-import
    Callable,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Union,
)

# Imports from Third Party Modules
import geocoder
import usaddress

# Local Imports
from scourgify.address_constants import (
    ABNORMAL_OCCUPANCY_ABBRVS,
    ADDRESS_KEYS,
    DIRECTIONAL_REPLACEMENTS,
    OCCUPANCY_TYPE_ABBREVIATIONS,
    STATE_ABBREVIATIONS,
    STREET_TYPE_ABBREVIATIONS,
)
from scourgify.cleaning import (
    clean_upper,
    post_clean_addr_str,
    pre_clean_addr_str,
    strip_occupancy_type,
)
from scourgify.exceptions import (
    AddressNormalizationError,
    AmbiguousAddressError,
    UnParseableAddressError,
)
from scourgify.validations import (
    validate_address_components,
    validate_parens_groups_parsed,
    validate_us_postal_code_format,
)

# Setup

# Constants

LINE1_USADDRESS_LABELS = (
    'AddressNumber',
    'StreetName',
    'AddressNumberPrefix',
    'AddressNumberSuffix',
    'StreetNamePreDirectional',
    'StreetNamePostDirectional',
    'StreetNamePreModifier',
    'StreetNamePostType',
    'StreetNamePreType',
    'IntersectionSeparator',
    'SecondStreetNamePreDirectional',
    'SecondStreetNamePostDirectional',
    'SecondStreetNamePreModifier',
    'SecondStreetNamePostType',
    'SecondStreetNamePreType',
    'LandmarkName',
    'CornerOf',
    'IntersectionSeparator',
    'BuildingName',
)
LINE2_USADDRESS_LABELS = (
    'OccupancyType',
    'OccupancyIdentifier',
    'SubaddressIdentifier',
    'SubaddressType',
)

LAST_LINE_LABELS = (
    'PlaceName',
    'StateName',
    'ZipCode',
)

AMBIGUOUS_LABELS = (
    'Recipient',
    'USPSBoxType',
    'USPSBoxID',
    'USPSBoxGroupType',
    'USPSBoxGroupID',
    'NotAddress'
)

STRIP_CHAR_CATS = (
    'M', 'S', 'C', 'Nl', 'No', 'Pc', 'Ps', 'Pe', 'Pi', 'Pf', 'Po'
)
STRIP_PUNC_CATS = ('Z', 'Pd')
STRIP_ALL_CATS = STRIP_CHAR_CATS + STRIP_PUNC_CATS


# Private Functions

# Public Classes and Functions

def normalize_address_record(address, addr_map=None, addtl_funcs=None,
                             strict=True):
    # type: (Union[str, Mapping[str, str]]) -> Mapping[str, str]
    """Normalize an address according to USPS pub. 28 standards.

    Takes an address string, or a dict-like with standard address fields
    (address_line_1, address_line_2, city, state, postal_code), removes
    unacceptable special characters, extra spaces, predictable abnormal
    character sub-strings and phrases, abbreviates directional indicators
    and street types.  If applicable, line 2 address elements (ie: Apt, Unit)
    are separated from line 1 inputs.

    addr_map, if used, must be in the format {standard_key: custom_key} based
    on standard address keys sighted above.

    Returns an address dict with all field values in uppercase format.

    :param address: str or dict-like object containing details of a single
        address.
    :type address: str | Mapping[str, str]
    :param addr_map: mapping of standard address fields to custom key names
    :type addr_map: Mapping[str, str]
    :param addtl_funcs: optional sequence of funcs that take string for further
        processing and return line1 and line2 strings
    :type addtl_funcs: Sequence[Callable[str, (str, str)]]
    :param strict: bool indicating strict handling of components address parts
        city, state and postal_code, vs city and state OR postal_code
    :return: address dict containing parsed and normalized address values.
    :rtype: Mapping[str, str]
    """
    if isinstance(address, str):
        return normalize_addr_str(address, addtl_funcs=addtl_funcs)
    else:
        return normalize_addr_dict(
            address, addr_map=addr_map, addtl_funcs=addtl_funcs, strict=strict
        )


def normalize_addr_str(addr_str,         # type: str
                       line2=None,       # type: Optional[str]
                       city=None,        # type: Optional[str]
                       state=None,       # type: Optional[str]
                       zipcode=None,     # type: Optional[str]
                       addtl_funcs=None  # type: Sequence[Callable[[str,str], str]]  # noqa
                      ):                                        # noqa
    # type (...) -> Mapping[str, str]                                        # noqa
    # type (...) -> Mapping[str, str]
    """Normalize a complete or partial address string.

    :param addr_str: str containing address data.
    :type addr_str: str
    :param line2: optional str containing occupancy or sub-address data
        (eg: Unit, Apt, Lot).
    :type line2: str
    :param city: optional str city name that does not need to be parsed from
        addr_str.
    :type city: str
    :param state: optional str state name that does not need to be parsed from
        addr_str.
    :type state: str
    :param zipcode: optional str postal code that does not need to be parsed
        from addr_str.
    :type zipcode: str
    :param addtl_funcs: optional sequence of funcs that take string for further
        processing and return line1 and line2 strings
    :type addtl_funcs: Sequence[Callable[str, (str, str)]]
    :return: address dict with uppercase parsed and normalized address values.
    :rtype: Mapping[str, str]
    """
    # get address parsed into usaddress components.
    error = None
    parsed_addr = None
    addr_str = pre_clean_addr_str(addr_str, normalize_state(state))
    try:
        parsed_addr = parse_address_string(addr_str)
    except (usaddress.RepeatedLabelError, AmbiguousAddressError) as err:
        error = err
        if not line2 and addtl_funcs:
            for func in addtl_funcs:
                try:
                    line1, line2 = func(addr_str)
                    error = False
                    # send refactored line_1 and line_2 back through processing
                    return normalize_addr_str(line1, line2=line2, city=city,
                                              state=state, zipcode=zipcode)
                except ValueError:
                    # try a different additional processing function
                    pass

    if parsed_addr and not parsed_addr.get('StreetName'):
        addr_dict = dict(
            address_line_1=addr_str, address_line_2=line2, city=city,
            state=state, postal_code=zipcode
        )
        full_addr = format_address_record(addr_dict)
        try:
            parsed_addr = parse_address_string(full_addr)
        except (usaddress.RepeatedLabelError, AmbiguousAddressError) as err:
            parsed_addr = None
            error = err

    if parsed_addr:
        parsed_addr = normalize_address_components(parsed_addr)
        zipcode = get_parsed_values(parsed_addr, zipcode, 'ZipCode', addr_str)
        city = get_parsed_values(parsed_addr, city, 'PlaceName', addr_str)
        state = get_parsed_values(parsed_addr, state, 'StateName', addr_str)
        state = normalize_state(state)

        # assumes if line2 is passed in that it need not be parsed from
        # addr_str. Primarily used to allow advanced processing of otherwise
        # unparsable addresses.
        line2 = line2 if line2 else get_normalized_line_segment(
            parsed_addr, LINE2_USADDRESS_LABELS
        )
        line2 = post_clean_addr_str(line2)
        # line 1 is fully post cleaned in get_normalized_line_segment.
        line1 = get_normalized_line_segment(
            parsed_addr, LINE1_USADDRESS_LABELS
        )
        validate_parens_groups_parsed(line1)
    else:
        # line1 is set to addr_str so complete dict can be passed to error.
        line1 = addr_str

    addr_rec = dict(
        address_line_1=line1, address_line_2=line2, city=city,
        state=state, postal_code=zipcode
    )
    if error:
        raise UnParseableAddressError(None, None, addr_rec)
    else:
        return addr_rec


def normalize_addr_dict(addr_dict, addr_map=None, addtl_funcs=None,
                        strict=True):
    # type: (Mapping[str, str]) -> Mapping[str, str]
    """Normalize an address from dict or dict-like object.

    Assumes addr_dict will have standard address related keys (address_line_1,
    address_line_2, city, state, postal_code), unless addr_map is provided.

    addr_map, if used, must be in the format {standard_key: custom_key} based
    on standard address keys sighted above.

    :param addr_dict: mapping containing address keys and values.
    :type addr_dict: Mapping
    :param addr_map: mapping of standard address fields to custom key names
    :type addr_map: Mapping[str, str]
    :param addtl_funcs: optional sequence of funcs that take string for further
        processing and return line1 and line2 strings
    :type addtl_funcs: Sequence[Callable[str, (str, str)]]
    :param strict: bool indicating strict handling of components address parts
        city, state and postal_code, vs city and state OR postal_code
    :return: address dict with normalized, uppercase address values.
    :rtype: Mapping[str, str]
    """
    if addr_map:
        addr_dict = {key: addr_dict.get(val) for key, val in addr_map.items()}
    addr_dict = validate_address_components(addr_dict, strict=strict)

    # line 1 and line 2 elements are combined to ensure consistent processing
    # whether the line 2 elements are pre-parsed or included in line 1
    addr_str = get_addr_line_str(addr_dict, comma_separate=True)
    postal_code = addr_dict.get('postal_code')
    zipcode = validate_us_postal_code_format(
        postal_code, addr_dict
    ) if postal_code else None
    city = addr_dict.get('city')
    state = addr_dict.get('state')
    try:
        address = normalize_addr_str(
            addr_str, city=city, state=state,
            zipcode=zipcode, addtl_funcs=addtl_funcs
        )
    except AddressNormalizationError:
        addr_str = get_addr_line_str(
            addr_dict, comma_separate=True, addr_parts=ADDRESS_KEYS
        )
        address = normalize_addr_str(
            addr_str, city=city, state=state,
            zipcode=zipcode, addtl_funcs=addtl_funcs
        )
    return address


def parse_address_string(addr_str):
    # type: (str) -> MutableMapping[str, str]
    """Separate an address string into its component parts per usaddress.

    Attempts to parse addr_str into it's component parts, using usaddress.

    If usaddress identifies the address type as Ambiguous or the resulting
    OrderedDict includes any keys from AMBIGUOUS_LABELS that would constitute
    ambiguous address in the SEED/GBR use case (ie: Recipient) then
    an AmbiguousAddressError is raised.

    :param addr_str: str address to be processed.
    :type addr_str: str
    :return: usaddress OrderedDict
    :rtype: MutableMapping
    """
    parsed_results = usaddress.tag(addr_str)
    parsed_addr = parsed_results[0]
    # if the address is parseable but some form of ambiguity is found that
    # may result in data corruption NormalizationError is raised.
    if (parsed_results[1] == 'Ambiguous' or
            any(key in AMBIGUOUS_LABELS for key in parsed_addr.keys())):
        raise AmbiguousAddressError()
    parsed_addr = handle_abnormal_occupancy(parsed_addr, addr_str)
    return parsed_addr


def handle_abnormal_occupancy(parsed_addr, addr_str):
    """Handle abnormal occupancy abbreviations that are parsed as street type.

    Evaluates addresses with an Occupancy or Subaddress identifier whose type
    may be parsed into StreetNamePostType and swaps the StreetNamePostType tag
    for the OccupancyType tag if necessary.

    For example: Portland Maps uses 'UN' as an abbreviation for 'Unit' which
    usaddress parses to 'StreetNamePostType' since 'UN' is correctly an
    abbreviation for 'Union' street type.
        123 MAIN UN => 123 MAIN UN
        123 MAIN UN A => 123 MAIN, UNIT A
        123 MAIN UN UN A => 123 MAIN UN, UNIT A

    :param parsed_addr: address parsed into usaddress components
    :type parsed_addr: OrderedDict
    :param addr_str: Original address string
    :type addr_str: str
    :return: parsed address
    :rtype: OrderedDict
    """
    occupancy_id_key = None
    occupany_type_key = 'OccupancyType'
    street_type_key = 'StreetNamePostType'
    occupany_type_keys = (occupany_type_key, 'SubaddressType')
    occupancy_identifier_keys = ('OccupancyIdentifier', 'SubaddressIdentifier')
    street_type = parsed_addr.get(street_type_key)
    if street_type in ABNORMAL_OCCUPANCY_ABBRVS:
        occupancy_type = None
        occupancy = None
        for key in occupany_type_keys:
            try:
                occupancy_type = parsed_addr[key]
                break
            except KeyError:
                pass
        for key in occupancy_identifier_keys:
            try:
                occupancy = parsed_addr[key]
                occupancy_id_key = key
                break
            except KeyError:
                break
        if occupancy and not occupancy_type:
            if street_type in occupancy:
                occupancy = occupancy.replace(street_type, '').strip()
                del parsed_addr[occupancy_id_key]
            else:
                line2 = "{} {}".format(street_type, occupancy)
                addr_str = addr_str.replace(line2, '')
                parsed_addr = parse_address_string(addr_str)
            parsed_addr.update({occupany_type_key: street_type})
            parsed_addr.update({occupancy_id_key: occupancy})
    return parsed_addr


def get_parsed_values(parsed_addr, orig_val, val_label, orig_addr_str):
    # type: (Mapping[str, str], str, str, str) -> Union[str, None]
    """Get valid values from parsed_addr corresponding to val_label.

    Retrieves values from parsed_addr corresponding to the label supplied in
    val_label.
    If a value for val_label is found in parsed_addr AND an orig_val is
    supplied, a single string will be returned if the values match. If only
    one of the two contains a non-null value.
    If both values are empty, None is returned.
    If the values an AmbiguousAddressError will be returned if the two values
    are not equal. This provides a check against misidentified address
    components when known values are available. (For example when a city is
    supplied from the address dict or record being normalized, but usaddress
    identifies extra information stored in address_line_1 as a PlaceName.)

    :param parsed_addr: address parsed into ordereddict per usaddress.
    :type parsed_addr: Mapping
    :param orig_val: related value passed in from incoming data source.
    :type orig_val: str
    :param val_label: label to locate in parsed_addr
    :type val_label: str
    :param orig_addr_str: address string to pass to error, if applicable.
    :type orig_addr_str: str
    :return: str | None
    """
    val_from_parse = parsed_addr.get(val_label)
    orig_val = post_clean_addr_str(orig_val)
    val_from_parse = post_clean_addr_str(val_from_parse)
    non_null_val_set = {orig_val, val_from_parse} - {None}
    if len(non_null_val_set) > 1:
        raise AmbiguousAddressError(None, None, orig_addr_str)
    else:
        return non_null_val_set.pop() if non_null_val_set else None


def normalize_address_components(parsed_addr):
    # type: (MutableMapping[str, str]) -> MutableMapping[str, str]
    """Normalize parsed sections of address as appropriate.

    Processes parsed address through subsets of normalization rules.

    :param parsed_addr: address parsed into ordereddict per usaddress.
    :type parsed_addr:Mapping
    :return: parsed_addr with normalization processing applied to elements.
    :rtype: dict
    """
    parsed_addr = normalize_numbered_streets(parsed_addr)
    parsed_addr = normalize_directionals(parsed_addr)
    parsed_addr = normalize_street_types(parsed_addr)
    parsed_addr = normalize_occupancy_type(parsed_addr)
    return parsed_addr


def normalize_numbered_streets(parsed_addr):
    # type: (MutableMapping[str, str]) -> MutableMapping[str, str]
    """Change numbered street names to include missing original identifiers.

    :param parsed_addr: address parsed into ordereddict per usaddress.
    :type parsed_addr: Mapping
    :return: parsed_addr with ordinal identifiers appended to numbered streets.
    :rtype: dict"""
    street_tags = ['StreetName', 'SecondStreetName']
    for tag in street_tags:
        post_type_tag = '{}PostType'.format(tag)
        # limits updates to numbered street names that include a post street
        # type, since an ordinal indicator would be inappropriate for some
        # numbered streets (ie. Country Road 97).
        if tag in parsed_addr.keys() and post_type_tag in parsed_addr.keys():
            try:
                cardinal = int(parsed_addr[tag])
                ord_indicator = get_ordinal_indicator(cardinal)
                parsed_addr[tag] = '{}{}'.format(cardinal, ord_indicator)
            except ValueError:
                pass
    return parsed_addr


def normalize_directionals(parsed_addr):
    # type: (MutableMapping[str, str]) -> MutableMapping[str, str]
    """Change directional notations to standard abbreviations.

    :param parsed_addr: address parsed into ordereddict per usaddress.
    :type parsed_addr: Mapping
    :return: parsed_addr with directionals updated to abbreviated format.
    :rtype: dict
    """
    # get the directional related keys from the current address.
    found_directional_tags = (
        tag for tag in parsed_addr.keys() if 'Directional' in tag
    )
    for found in found_directional_tags:
        # get the original directional related value per key.
        dir_str = parsed_addr[found]
        # remove spaces, punctuation, hyphens etc so two part directions
        # conform to a single word standard. Convert to upper case
        dir_str = clean_upper(
            dir_str, exclude=[], removal_cats=STRIP_ALL_CATS, strip_spaces=True
        )
        if dir_str in DIRECTIONAL_REPLACEMENTS.keys():
            parsed_addr[found] = DIRECTIONAL_REPLACEMENTS[dir_str]
    return parsed_addr


def normalize_street_types(parsed_addr):
    # type: (MutableMapping[str, str]) -> MutableMapping[str, str]
    """Change street types to accepted abbreviated format.

    No change is made if street types do not conform to common usages per
    USPS pub 28 appendix C.

    :param parsed_addr: address parsed into ordereddict per usaddress.
    :type parsed_addr: Mapping
    :return: parsed_addr with street types updated to abbreviated format.
    :rtype: dict
    """
    # get the *Street*Type keys from the current parsed address.
    found_type_tags = (
        tag for tag in parsed_addr.keys() if 'Street' in tag and 'Type' in tag
    )
    for found in found_type_tags:
        # lookup the appropriate abbrev for the street type found per key.
        type_abbr = STREET_TYPE_ABBREVIATIONS.get(parsed_addr[found])
        # update the street type only if a new abbreviation is found.
        if type_abbr:
            parsed_addr[found] = type_abbr
    return parsed_addr


def normalize_occupancy_type(parsed_addr, default=None):
    # type: (MutableMapping[str, str]) -> MutableMapping[str, str]
    """Change occupancy types to accepted abbreviated format.

    If there is an occupancy and it does not conform to one of the
    OCCUPANCY_TYPE_ABBREVIATIONS, occupancy is changed to the generic 'UNIT'.
    OCCUPANCY_TYPE_ABBREVIATIONS contains common abbreviations per
    USPS pub 28 appendix C, however, OCCUPANCY_TYPE_ABBREVIATIONS can be
    customized to allow alternate abbreviations to pass through. (see README)

    :param parsed_addr: address parsed into ordereddict per usaddress.
    :type parsed_addr: Mapping
    :param default: default abbreviation to use for types that fall outside the
     standard abbreviations. Default is 'UNIT'
    :return: parsed_addr with occupancy types updated to abbreviated format.
    :rtype: dict
    """
    default = default if default is not None else 'UNIT'
    occupancy_type_label = 'OccupancyType'
    occupancy_type = parsed_addr.pop(occupancy_type_label, None)
    occupancy_type_abbr = (
        occupancy_type
        if occupancy_type in OCCUPANCY_TYPE_ABBREVIATIONS.values()
        else OCCUPANCY_TYPE_ABBREVIATIONS.get(occupancy_type)
    )
    occupancy_id = parsed_addr.get('OccupancyIdentifier')
    if ((occupancy_id and not occupancy_id.startswith('#'))
            and not occupancy_type_abbr):
        occupancy_type_abbr = default
    if occupancy_type_abbr:
        parsed_list = list(parsed_addr.items())
        index = parsed_list.index(('OccupancyIdentifier', occupancy_id))
        parsed_list.insert(index, (occupancy_type_label, occupancy_type_abbr))
        parsed_addr = OrderedDict(parsed_list)
    return parsed_addr


def normalize_state(state):
    # type: (Union[str, None]) -> Union[str, None]
    """Change state string to accepted abbreviated format.

    :param state: string containing state name or abbreviation.
    :type state: str | None
    :return: 2 char state abbreviation, or original state string if not found
        in state names or standard long abbreviations.
    :rtype: str | None
    """
    if state:
        state_abbrv = STATE_ABBREVIATIONS.get(state.upper())
        if state_abbrv:
            state = state_abbrv
    return state


def get_normalized_line_segment(parsed_addr, line_labels):
    # type: (Mapping[str, str], Sequence[str]) -> str
    """

    :param parsed_addr: address parsed into ordereddict per usaddress.
    :param line_labels: tuple of str labels of all the potential keys related
        to the desired address segment (ie address_line_1 or address_line_2).
    :return: s/r joined values from parsed_addr corresponding to given labels.
    """
    line_elems = [
        elem for key, elem in parsed_addr.items() if key in line_labels
    ]
    line_str = ' '.join(line_elems) if line_elems else None
    return post_clean_addr_str(line_str)


def get_addr_line_str(addr_dict, addr_parts=None, comma_separate=False):
    # type: (Mapping[str, str], Optional[Sequence], bool) -> str
    """Get address 'line' elements as a single string.

    Combines 'address_line_1' and 'address_line_2' elements as a single string
    to ensure no data is lost and line_2 can be processed according to a
    standard set of rules.

    :param addr_dict: dict containing keys 'address_line_1', 'address_line_2'.
    :type addr_dict: Mapping
    :param addr_parts: optional sequence of address elements
    :type addr_parts:
    :param comma_separate: optional boolean to separate dict values by comma
        useful for dealing with potentially ambiguous line 2 segments
    :type bool:
    :return: string combining 'address_line_1' & 'address_line_2' values.
    :rtype: str
    """
    if not addr_parts:
        addr_parts = ['address_line_1', 'address_line_2']
    if not isinstance(addr_parts, (list, tuple)):
        raise TypeError('addr_parts must be a list or tuple')
    separator = ', ' if comma_separate else ' '
    addr_str = separator.join(
        str(addr_dict[elem]) for elem in addr_parts if addr_dict.get(elem)
    )
    return addr_str


def format_address_record(address):
    # type AddressRecord -> str
    """Format AddressRecord as string."""
    address_template = Template('$address')
    address = dict(address)
    addr_parts = [
        str(address[field]) for field in ADDRESS_KEYS if address.get(field)
    ]
    return address_template.safe_substitute(address=', '.join(addr_parts))


def get_geocoder_normalized_addr(address, addr_keys=ADDRESS_KEYS):
    # type: (Union[Mapping, str], Optional[Sequence]) -> dict
    """Get geocoder normalized address parsed to dict with addr_keys.

    :param address: string or dict-like containing address data
    :param addr_keys: optional list of address keys. standard list of keys will
        be used if not supplied
    :return: dict containing geocoder address result
    """
    address_line_2 = None
    geo_addr_dict = {}
    if not isinstance(address, str):
        address_line_2 = address.get('address_line_2')
        address = get_addr_line_str(address, addr_parts=addr_keys)
    geo_resp = geocoder.google(address)
    if geo_resp.ok and geo_resp.housenumber:
        line2 = geo_resp.subpremise or address_line_2
        geo_addr_dict = {
            'address_line_1':
                ' '.join([geo_resp.housenumber, geo_resp.street]),
            'address_line_2': strip_occupancy_type(line2),
            'city': geo_resp.city,
            'state': geo_resp.state,
            'postal_code': geo_resp.postal
        }
        for key, value in geo_addr_dict.items():
            geo_addr_dict[key] = value.upper() if value else None
    return geo_addr_dict


def get_ordinal_indicator(number):
    # type: (int) -> str
    """Get the ordinal indicator suffix applicable to the supplied number.

     Ordinal numbers are words representing position or rank in a sequential
     order (1st, 2nd, 3rd, etc).
     Ordinal indicators are the suffix characters (st, nd, rd, th) that, when
     applied to a numeral (int), denote that it an ordinal number.

    :param number: int
    :type: int
    :return: ordinal indicator appropriate to the number supplied.
    :rtype: str
    """
    str_num = str(number)
    digits = len(str_num)
    if str_num[-1] == '1' and not (digits >= 2 and str_num[-2:] == '11'):
        return 'st'
    elif str_num[-1] == '2' and not (digits >= 2 and str_num[-2:] == '12'):
        return 'nd'
    elif str_num[-1] == '3' and not (digits >= 2 and str_num[-2:] == '13'):
        return 'rd'
    else:
        return 'th'
