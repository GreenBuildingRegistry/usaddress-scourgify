#!/usr/bin/env python
# encoding: utf-8
"""
copyright (c) 2016-2017 Earth Advantage.
All rights reserved
..codeauthor::Fable Turas <fable@rainsoftware.tech>

Custom errors pertaining to address normalization.
"""


# Private Functions


# Public Classes and Functions

class AddressNormalizationError(Exception):
    """Indicates error during normalization"""
    TITLE = None
    MESSAGE = None

    def __init__(self, error=None, title=None, *args):
        self.error = error or self.MESSAGE
        self.title = title or self.TITLE
        args = (error, title) + args
        super(AddressNormalizationError, self).__init__(*args)

    def __str__(self):
        msg = "{}: {}".format(self.title, self.error)
        if len(self.args) > 2:
            msg = "{}, {}".format(
                msg, ', '.join(str(a) for a in self.args[2:])
            )
        return msg


class AmbiguousAddressError(AddressNormalizationError):
    """Indicates an error from ambiguous addresses or address parts."""
    MESSAGE = "This address contains ambiguous elements."
    TITLE = "AMBIGUOUS ADDRESS"


class UnParseableAddressError(AddressNormalizationError):
    """Indicates an error from addresses that cannot be parsed."""
    MESSAGE = "Unable to break this address into its component parts"
    TITLE = "UNPARSEABLE ADDRESS"


class IncompleteAddressError(AddressNormalizationError):
    """Indicates error from addresses that don't have enough data to index."""
    MESSAGE = "This address is missing one or more required elements"
    TITLE = "INCOMPLETE ADDRESS"


class AddressValidationError(AddressNormalizationError):
    """Indicates address elements that don't meet format standards."""
    MESSAGE = "Address contains invalid formatting"
    TITLE = "ADDRESS FORMAT VALIDATION"
