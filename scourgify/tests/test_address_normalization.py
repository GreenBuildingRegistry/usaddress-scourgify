#!/usr/bin/env python
# encoding: utf-8
"""
copyright (c) 2016-2019 Earth Advantage.
All rights reserved

Unit tests for scourgify.
"""

# Imports from Standard Library
from collections import OrderedDict
from unittest import TestCase, mock

# Imports from Third Party Modules
from yamlconf import ConfigError

# Local Imports
from scourgify import address_constants
from scourgify.cleaning import (
    clean_ambiguous_street_types,
    clean_period_char,
    post_clean_addr_str,
    pre_clean_addr_str,
)
from scourgify.exceptions import (
    AddressNormalizationError,
    AddressValidationError,
    AmbiguousAddressError,
    IncompleteAddressError,
    UnParseableAddressError,
)
from scourgify.normalize import (
    get_addr_line_str,
    get_geocoder_normalized_addr,
    get_normalized_line_segment,
    get_ordinal_indicator,
    get_parsed_values,
    normalize_addr_dict,
    normalize_addr_str,
    normalize_address_record,
    normalize_directionals,
    normalize_numbered_streets,
    normalize_occupancy_type,
    normalize_state,
    normalize_street_types,
    parse_address_string,
)
from scourgify.validations import (
    validate_address_components,
    validate_parens_groups_parsed,
    validate_us_postal_code_format,
)

# Constants
SERVICE = 'GBR Test Normalization'
# Helper Functions & Classes


# Tests
class TestAddressNormalization(TestCase):
    """Unit tests for scourgify"""
    # pylint:disable=too-many-arguments

    def setUp(self):
        """setUp"""
        self.expected = dict(
            address_line_1='123 NOWHERE ST',
            address_line_2='STE 0',
            city='BORING',
            state='OR',
            postal_code='97009'
        )
        self.address_dict = dict(
            address_line_1='123 Nowhere St',
            address_line_2='Suite 0',
            city='Boring',
            state='OR',
            postal_code='97009'
        )

        self.ordinal_addr = dict(
            address_line_1='4333 NE 113th',
            city='Boring',
            state='OR',
            postal_code='97009'
        )
        self.ordinal_expected = dict(
            address_line_1='4333 NE 113TH',
            address_line_2=None,
            city='BORING',
            state='OR',
            postal_code='97009'
        )
        self.parseable_addr_str = '123 Nowhere Street Suite 0 Boring OR 97009'
        self.parsed_addr = OrderedDict([
            ('AddressNumber', '123'),
            ('StreetName', 'NOWHERE'),
            ('StreetNamePostType', 'STREET'),
            ('OccupancyType', 'SUITE'),
            ('OccupancyIdentifier', '0'),
            ('PlaceName', 'BORING'),
            ('StateName', 'OR'),
            ('ZipCode', '97009')
        ])
        self.unparesable_addr_str = '6000 SW 1000TH AVE  (BLDG  A5 RIGHT)'

    def test_normalize_address_record(self):
        """Test normalize_address_record function."""
        result = normalize_address_record(self.parseable_addr_str)
        self.assertDictEqual(self.expected, result)

        result = normalize_address_record(self.address_dict)
        self.assertDictEqual(self.expected, result)

        result = normalize_address_record(self.ordinal_addr)
        self.assertDictEqual(self.ordinal_expected, result)

    def test_normalize_addr_str(self):
        """Test normalize_addr_str function."""
        result = normalize_addr_str(self.parseable_addr_str)
        self.assertDictEqual(self.expected, result)

        broken_line1 = '6000 SW 1000TH AVE '
        broken_line2 = '(BLDG  A1 RIGHT)'
        result = normalize_addr_str(
            broken_line1, line2=broken_line2,
            city='Portland', state='OR', zipcode='97203'
        )
        expected = {
            'address_line_1': '6000 SW 1000TH AVE',
            'address_line_2': 'BLDG A1 RIGHT',
            'state': 'OR', 'city': 'PORTLAND',
            'postal_code': '97203'
        }
        self.assertDictEqual(expected, result)

        def addtl_test_func(addr_str):
            if 'BLDG A1' in addr_str:
                return '123 NOWHERE STREET', 'BLDG A1 RIGHT'
            else:
                raise ValueError

        addtl_processing = '123 Nowhere Street (BLDG A1 RIGHT)'
        expected = {
            'address_line_1': '123 NOWHERE ST',
            'address_line_2': 'BLDG A1 RIGHT',
            'state': 'OR', 'city': 'PORTLAND',
            'postal_code': '97203'
        }
        result = normalize_addr_str(
            addtl_processing, city='Portland', state='OR', zipcode='97203',
            addtl_funcs=[addtl_test_func]
        )
        self.assertDictEqual(expected, result)

        self.assertRaises(
            UnParseableAddressError,
            normalize_addr_str,
            self.unparesable_addr_str,
            city='Portland', state='OR', zipcode='97203',
            addtl_funcs=[addtl_test_func]

        )

    def test_normalize_addr_dict(self):
        """Test normalize_addr_dict function."""
        result = normalize_addr_dict(self.address_dict)
        self.assertDictEqual(self.expected, result)

        alternate_dict = dict(
            address1='123 Nowhere St',
            address2='Suite 0',
            city='Boring',
            state='OR',
            zip='97009'
        )
        dict_map = {
            'address_line_1': 'address1',
            'address_line_2': 'address2',
            'city': 'city',
            'state': 'state',
            'postal_code': 'zip'
        }
        result = normalize_addr_dict(alternate_dict, addr_map=dict_map)
        self.assertDictEqual(self.expected, result)

    def test_parse_address_string(self):
        """Test parse_address_string function."""
        result = parse_address_string(self.parseable_addr_str)
        self.assertIsInstance(result, OrderedDict)

        ambig_addr_str = 'AWBREY VILLAGE'
        with self.assertRaises(AmbiguousAddressError):
            parse_address_string(ambig_addr_str)

    def test_normalize_occupancies(self):
        """Test normalize_addr_dict function with handling for occupancy
        type oddities.  This is based on a real life incident; the original
        behavior to allow non-standard unit types to pass through resulted
        in an address validation service also allowing the address to pass
        through even though no unit should have existed on the home.
        """
        dict_map = {
            'address_line_1': 'address1',
            'address_line_2': 'address2',
            'city': 'city',
            'state': 'state',
            'postal_code': 'zip'
        }

        weird_unit = dict(
            address1='123 Nowhere St',
            address2='Ave 345',
            city='Boring',
            state='OR',
            zip='97009'
        )
        expected = dict(
            address_line_1='123 NOWHERE ST',
            address_line_2='UNIT 345',
            city='BORING',
            state='OR',
            postal_code='97009'
        )
        result = normalize_addr_dict(weird_unit, addr_map=dict_map)
        self.assertDictEqual(expected, result)

        late_unit_add = dict(
            address1='123 Nowhere St',
            address2='345',
            city='Boring',
            state='OR',
            zip='97009'
        )
        result = normalize_addr_dict(late_unit_add, addr_map=dict_map)
        self.assertDictEqual(expected, result)

        expected = dict(
            address_line_1='123 NOWHERE ST',
            address_line_2='# 345',
            city='BORING',
            state='OR',
            postal_code='97009'
        )

        hashtag_unit = dict(
            address1='123 Nowhere St',
            address2='# 345',
            city='Boring',
            state='OR',
            zip='97009'
        )
        result = normalize_addr_dict(hashtag_unit, addr_map=dict_map)
        self.assertDictEqual(expected, result)

        hashtag_unit = dict(
            address1='123 Nowhere St',
            address2='#345',
            city='Boring',
            state='OR',
            zip='97009'
        )
        result = normalize_addr_dict(hashtag_unit, addr_map=dict_map)
        self.assertDictEqual(expected, result)

        expected = dict(
            address_line_1='123 NOWHERE ST',
            address_line_2='APT 345',
            city='BORING',
            state='OR',
            postal_code='97009'
        )

        abbreviation = dict(
            address1='123 Nowhere St',
            address2='Apt 345',
            city='Boring',
            state='OR',
            zip='97009'
        )
        result = normalize_addr_dict(abbreviation, addr_map=dict_map)
        self.assertDictEqual(expected, result)

        full_name = dict(
            address1='123 Nowhere St',
            address2='Apartment 345',
            city='Boring',
            state='OR',
            zip='97009'
        )
        result = normalize_addr_dict(full_name, addr_map=dict_map)
        self.assertDictEqual(expected, result)


class TestAddressNormalizationUtils(TestCase):
    """Unit tests for scourgify utils"""

    def setUp(self):

        self.address_dict = dict(
            address_line_1='123 Nowhere St',
            address_line_2='Suite 0',
            city='Boring',
            state='OR',
            postal_code='97009'
        )
        self.parseable_addr = '123 Nowhere Street Suite 0 Boring OR 97009'
        self.parsed_addr = OrderedDict([
            ('AddressNumber', '123'),
            ('StreetName', 'NOWHERE'),
            ('StreetNamePostType', 'STREET'),
            ('OccupancyType', 'SUITE'),
            ('OccupancyIdentifier', '0'),
            ('PlaceName', 'BORING'),
            ('StateName', 'OR'),
            ('ZipCode', '97009')
        ])

        self.unparesable_addr = '6000 SW 1000TH AVE  (BLDG  A1 RIGHT)'

        self.unparesable_addr_dict = OrderedDict([
            ('AddressNumber', '6000'),
            ('StreetNamePreDirectional', 'SW'),
            ('StreetName', '1000TH'),
            ('StreetNamePostType', 'AVE'),
            ('SubaddressType', 'BLDG'),
            ('SubaddressIdentifier', 'A1'),
            ('SubaddressType', 'RIGHT')
        ])

    def test_get_parsed_values(self):
        """Test get_parsed_values function."""
        expected = 'BORING'
        result = get_parsed_values(self.parsed_addr, 'Boring',
                                   'PlaceName', self.parseable_addr)
        self.assertEqual(expected, result)

        expected = 'ONE VALUE PRESENT'
        result = get_parsed_values(self.parsed_addr, 'One Value Present',
                                   'LandmarkName', self.parseable_addr)
        self.assertEqual(expected, result)

        result = get_parsed_values(self.parsed_addr, None,
                                   'LandmarkName', self.parseable_addr)
        self.assertIsNone(result)

        with self.assertRaises(AmbiguousAddressError):
            get_parsed_values(self.parsed_addr, 'UnMatched City',
                              'PlaceName', self.parseable_addr)

    def test_get_norm_line_segment(self):
        """Test get normalized_line_segment function."""
        result = get_normalized_line_segment(self.parsed_addr,
                                             ['StreetName', 'AddressNumber'])
        expected = '{} {}'.format(self.parsed_addr['AddressNumber'],
                                  self.parsed_addr['StreetName'])
        self.assertEqual(expected, result)

        result = get_normalized_line_segment(
            self.parsed_addr,
            ['StreetName', 'StreetNamePostType', 'IntersectionSeparator']
        )
        expected = '{} {}'.format(self.parsed_addr['StreetName'],
                                  self.parsed_addr['StreetNamePostType'])
        self.assertEqual(expected, result)

    def test_normalize_numbered_streets(self):
        """Test normalize_numbered_streets function."""
        numbered_addr = OrderedDict([
            ('AddressNumber', '123'),
            ('StreetName', '100'),
            ('StreetNamePostType', 'STREET')
        ])
        county_road = OrderedDict([
            ('AddressNumber', '123'),
            ('StreetNamePreType', 'COUNTY ROAD'),
            ('StreetName', '100')
        ])
        string_addr = OrderedDict([
            ('AddressNumber', '123'),
            ('StreetName', '91st'),
            ('StreetNamePostType', 'STREET')
        ])

        expected = '{}{}'.format(
            numbered_addr['StreetName'], 'th'
        )
        result = normalize_numbered_streets(numbered_addr)
        self.assertEqual(expected, result['StreetName'])

        result = normalize_numbered_streets(county_road)
        self.assertDictEqual(county_road, result)

        result = normalize_numbered_streets(string_addr)
        self.assertDictEqual(string_addr, result)

    def test_normalize_directionals(self):
        """Test normalize_directionals function."""
        unabbr_directional = OrderedDict([
            ('AddressNumber', '123'),
            ('StreetNamePreDirectional', 'South West', ),
            ('StreetName', '100'),
            ('StreetNamePostType', 'STREET')
        ])
        abbrev_directional = OrderedDict([
            ('AddressNumber', '123'),
            ('SW', 'StreetNamePreDirectional'),
            ('StreetNamePreType', 'COUNTY ROAD'),
            ('StreetName', '100')
        ])
        no_directional = OrderedDict([
            ('AddressNumber', '123'),
            ('StreetName', '91st'),
            ('StreetNamePostType', 'STREET')
        ])

        expected = 'SW'
        result = normalize_directionals(unabbr_directional)
        self.assertEqual(expected, result['StreetNamePreDirectional'])

        result = normalize_directionals(abbrev_directional)
        self.assertDictEqual(abbrev_directional, result)

        result = normalize_directionals(no_directional)
        self.assertDictEqual(no_directional, result)

    def test_normalize_street_types(self):
        """Test normalize_street_types function."""
        unabbr_type = OrderedDict([
            ('AddressNumber', '123'),
            ('StreetNamePreDirectional', 'SW', ),
            ('StreetName', 'MAIN'),
            ('StreetNamePostType', 'STREET')
        ])
        abbrev_type = OrderedDict([
            ('AddressNumber', '123'),
            ('StreetNamePreDirectional', 'SW', ),
            ('StreetName', 'MAIN'),
            ('StreetNamePostType', 'AVE')
        ])
        typo_type = OrderedDict([
            ('AddressNumber', '123'),
            ('StreetNamePreDirectional', 'SW', ),
            ('StreetName', 'MAIN'),
            ('StreetNamePostType', 'STROET')
        ])
        no_type = OrderedDict([
            ('AddressNumber', '123'),
            ('StreetNamePreDirectional', 'SW', ),
            ('StreetName', 'MAIN'),
        ])

        expected = 'ST'
        result = normalize_street_types(unabbr_type)
        self.assertEqual(expected, result['StreetNamePostType'])

        result = normalize_street_types(abbrev_type)
        self.assertDictEqual(abbrev_type, result)

        result = normalize_street_types(typo_type)
        self.assertDictEqual(typo_type, result)

        result = normalize_street_types(no_type)
        self.assertDictEqual(no_type, result)

    def test_normalize_occupancy_type(self):
        """Test normalize_occupancy_type function."""
        expected = 'STE'
        result = normalize_occupancy_type(self.parsed_addr)
        self.assertEqual(expected, result['OccupancyType'])

    def test_normalize_state(self):
        """Test normalize_state function"""
        state = 'ore'
        expected = 'OR'
        result = normalize_state(state)
        self.assertEqual(expected, result)

        state = 'oregano'
        expected = state
        result = normalize_state(state)
        self.assertEqual(expected, result)

        self.assertIsNone(normalize_state(None))

    def test_pre_clean_addr_str(self):
        """Test pre_clean_addr_str function"""
        odd_addr = '123 Nowhere    Street, Suite 0; @Boring OR 97009'
        # we're leaving commas in the pre-clean until norm can be revisited
        expected = '123 Nowhere Street, Suite 0 Boring OR 97009'.upper()
        # expected = '123 Nowhere Street Suite 0 Boring OR 97009'.upper()
        result = pre_clean_addr_str(odd_addr)
        self.assertEqual(expected, result)

    def test_post_clean_addr_str(self):
        """Test post_clean_addr_str function."""
        addr_str = '(100-104) SW NO   WHERE st'
        expected = '100-104 SW NO WHERE ST'
        result = post_clean_addr_str(addr_str)
        self.assertEqual(expected, result)

        self.assertIsNone(post_clean_addr_str(None))
        self.assertEqual('', post_clean_addr_str(''))

    def test_validate_address(self):
        """Test validate_address_components function."""
        expected = self.address_dict
        result = validate_address_components(self.address_dict)
        self.assertEqual(expected, result)

        minus_line1 = dict(
            address_line_1=None,
            address_line_2='Suite 0',
            city='Boring',
            state='OR',
            postal_code='97009'
        )
        with self.assertRaises(IncompleteAddressError):
            validate_address_components(minus_line1)

        minus_zip = dict(
            address_line_1='123 NoWhere St',
            address_line_2='Suite 0',
            city='Boring',
            state='OR',
            postal_code=None
        )
        with self.assertRaises(IncompleteAddressError):
            validate_address_components(minus_zip)

        minus_city_state = dict(
            address_line_1='123 NoWhere St',
            address_line_2='Suite 0',
            city=None,
            state=None,
            postal_code='97009'
        )

        with self.assertRaises(IncompleteAddressError):
            validate_address_components(minus_city_state)

        minus_city_state_zip = dict(
            address_line_1='123 NoWhere St',
            address_line_2='Suite 0',
            city=None,
            state=None,
            postal_code=None
        )
        with self.assertRaises(IncompleteAddressError):
            validate_address_components(minus_city_state_zip)

    def test_validate_postal_code(self):
        """Test validate_us_postal_code_format"""

        with self.assertRaises(AddressValidationError):
            zip_plus = '97219-0001-00'
            validate_us_postal_code_format(zip_plus, self.address_dict)

        with self.assertRaises(AddressValidationError):
            zip_plus = '97219-00'
            validate_us_postal_code_format(zip_plus, self.address_dict)

        with self.assertRaises(AddressValidationError):
            zip_plus = '972-0001'
            validate_us_postal_code_format(zip_plus, self.address_dict)

        with self.assertRaises(AddressValidationError):
            zip_five = '9721900'
            validate_us_postal_code_format(zip_five, self.address_dict)

        with self.assertRaises(AddressValidationError):
            zip_five = '972'
            validate_us_postal_code_format(zip_five, self.address_dict)

        expected = '97219'
        result = validate_us_postal_code_format(expected, self.address_dict)
        self.assertEqual(expected, result)

    def test_get_addr_line_str(self):
        """Test get_addr_line_str function."""
        expected = '{} {}'.format(
            self.address_dict['address_line_1'],
            self.address_dict['address_line_2']
        )
        result = get_addr_line_str(self.address_dict)
        self.assertEqual(expected, result)

        no_line_2 = {
            'address_line_1': 'address line 1'
        }
        expected = no_line_2['address_line_1']
        result = get_addr_line_str(no_line_2)
        self.assertEqual(expected, result)

        empty_line_2 = {
            'address_line_1': 'address line 1',
            'address_line_2': None
        }
        expected = no_line_2['address_line_1']
        result = get_addr_line_str(empty_line_2)
        self.assertEqual(expected, result)

        with self.assertRaises(TypeError):
            get_addr_line_str(self.address_dict, addr_parts='line1')

    @mock.patch(
        'scourgify.normalize.geocoder'
    )
    def test_get_geocoder_normalized_addr(self, mock_geocoder):
        """Test get_geocoder_normalized_addr"""
        geo_addr = mock.MagicMock()
        geo_addr.ok = True
        geo_addr.housenumber = '1234'
        geo_addr.street = "Main"
        geo_addr.subpremise = ''
        geo_addr.city = 'Boring'
        geo_addr.state = 'OR'
        geo_addr.postal = '97000'

        mock_geocoder.google.return_value = geo_addr

        address = {
            'address_line_1': '1234 Main',
            'address_line_2': None,
            'city': 'Boring',
            'state': 'OR',
            'postal_code': '97000'
        }
        addr_str_return_value = "1234 Main Boring OR 97000"
        get_geocoder_normalized_addr(address)
        mock_geocoder.google.assert_called_with(addr_str_return_value)

    def test_get_ordinal_indicator(self):
        """Test get_ordinal_indicator"""
        result = get_ordinal_indicator(11)
        expected = 'th'
        self.assertEqual(expected, result)

        result = get_ordinal_indicator(112)
        self.assertEqual(expected, result)

        result = get_ordinal_indicator(3113)
        self.assertEqual(expected, result)

        result = get_ordinal_indicator(1)
        expected = 'st'
        self.assertEqual(expected, result)

        result = get_ordinal_indicator(22)
        expected = 'nd'
        self.assertEqual(expected, result)

        result = get_ordinal_indicator(31243)
        expected = 'rd'
        self.assertEqual(expected, result)

    def test_clean_period_char(self):
        """Test clean_period_char"""
        text = "49.5 blah.blah."
        expected = "49.5 blahblah"
        result = clean_period_char(text)
        self.assertEqual(expected, result)

    def test_validate_parens_group_parsed(self):
        """Test validate_parens_groups_parsed"""
        broken_line1 = '6000 SW 1000TH AVE'
        result = validate_parens_groups_parsed(broken_line1)
        self.assertEqual(broken_line1, result)

        bad_addr = '10000 NE 8TH (ROW HOUSE)'
        with self.assertRaises(AmbiguousAddressError):
            validate_parens_groups_parsed(bad_addr)

    def test_clean_ambiguous_street_types(self):
        """ Test clean_ambiguous_street_types"""
        problem_addr = "1234 BROKEN CT"
        expected = "1234 BROKEN COURT"
        result = clean_ambiguous_street_types(problem_addr)
        self.assertEqual(expected, result)

        normal_addr = "1234 NORMAL ST"
        result = clean_ambiguous_street_types(normal_addr)
        self.assertEqual(normal_addr, result)

    def test_address_normalization_error(self):
        error_msg = 'Error Message'
        error_title = 'ERROR TITLE'
        addtl_args = 'Addition info'
        expected = "{}: {}, {}".format(error_title, error_msg, addtl_args)
        error = AddressNormalizationError(error_msg, error_title, addtl_args)
        self.assertEqual(expected, str(error))

    @mock.patch.object(address_constants.NormalizationConfig, 'get')
    def test_set_constants(self, mock_config_get):
        new_addr_keys = ['new keys']
        new_problem_st = {
            "PS": 'STREET'
        }
        mock_config_get.side_effect = (
            'update', new_addr_keys,
            None, None, None, None, None,
            new_problem_st
        )
        address_constants.set_address_constants()
        self.assertEqual(address_constants.ADDRESS_KEYS, new_addr_keys)
        self.assertIn("PS", address_constants.PROBLEM_ST_TYPE_ABBRVS.keys())

        mock_config_get.side_effect = (
            'replace', new_addr_keys,
            None, None, None, None, None,
            new_problem_st
        )
        address_constants.set_address_constants()
        self.assertEqual(address_constants.ADDRESS_KEYS, new_addr_keys)
        self.assertDictEqual(
            new_problem_st, address_constants.PROBLEM_ST_TYPE_ABBRVS
        )

        mock_config_get.side_effect = (
            'invalid', new_addr_keys,
            None, None, None, None, None,
            new_problem_st
        )
        self.assertRaises(
            ConfigError, address_constants.set_address_constants
        )

    def test_handle_abnormal_occupancy(self):
        addr_str = '123 SW MAIN UN'
        expected = OrderedDict([
            ('AddressNumber', '123'),
            ('StreetNamePreDirectional', 'SW'),
            ('StreetName', 'MAIN'),
            ('StreetNamePostType', 'UN'),
        ])
        result = parse_address_string(addr_str)
        self.assertEqual(expected, result)

        addr_str = '123 SW MAIN UN A'
        expected = OrderedDict([
            ('AddressNumber', '123'),
            ('StreetNamePreDirectional', 'SW'),
            ('StreetName', 'MAIN'),
            ('OccupancyType', 'UN'),
            ('OccupancyIdentifier', 'A')
        ])
        result = parse_address_string(addr_str)
        self.assertEqual(expected, result)

        addr_str = '123 SW MAIN UN, UN A'
        expected = OrderedDict([
            ('AddressNumber', '123'),
            ('StreetNamePreDirectional', 'SW'),
            ('StreetName', 'MAIN'),
            ('StreetNamePostType', 'UN'),
            ('OccupancyType', 'UN'),
            ('OccupancyIdentifier', 'A')
        ])
        result = parse_address_string(addr_str)
        self.assertEqual(expected, result)
