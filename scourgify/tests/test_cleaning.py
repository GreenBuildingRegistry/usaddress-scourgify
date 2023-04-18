#!/usr/bin/env python
# encoding: utf-8
"""
copyright (c) 2016-2019 Earth Advantage.
All rights reserved
"""

# Imports from Standard Library
from unittest import TestCase

# Local Imports
from scourgify.cleaning import strip_occupancy_type


class CleaningTests(TestCase):

    def test_strip_occupancy_type(self):
        expected = '33'

        line2 = 'Unit 33'
        result = strip_occupancy_type(line2)
        self.assertEqual(result, expected)

        line2 = 'Apartment 33'
        result = strip_occupancy_type(line2)
        self.assertEqual(result, expected)

        line2 = 'Unit #33'
        result = strip_occupancy_type(line2)
        self.assertEqual(result, expected)

        line2 = 'Building 3 Unit 33'
        result = strip_occupancy_type(line2)
        self.assertEqual(result, expected)

        line2 = 'Building 3 UN 33'
        result = strip_occupancy_type(line2)
        self.assertEqual(result, expected)

        line2 = '33'
        result = strip_occupancy_type(line2)
        self.assertEqual(result, expected)
