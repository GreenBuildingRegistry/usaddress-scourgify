usaddress-scourgify
===================

A Python library for cleaning/normalizing US addresses following USPS pub 28 and RESO guidelines.



Documentation
-------------
Use

``normalize_address_record()``

 or

``get_geocoder_normalized_addr()``

to standardize your addresses. (Note: usaddress-scourgify does not make any attempts at address validation.)

Both functions take an address string, or a dict-like object, and return an address dict with all field values in uppercase format mapped to the keys address_line_1, address_line_2, city, state, postal_code.


normalized_address_record() uses the included processing functions to remove unacceptable special characters, extra spaces, predictable abnormal character sub-strings and phrases. It also abbreviates directional indicators and street types according to the abbreviation mappings found in address_constants.  If applicable, line 2 address elements (ie: Apt, Unit) are separated from line 1 inputs and standard occupancy type abbreviations are applied.

You may supply additional additional processing functions as a list of callable supplied to the addtl_funcs parameter. Any additional functions should take a string address and return a tuple of strings (line1, line2).

If your address is in the form of a dict that does not use the keys address_line_1, address_line_2, city, state, and postal_code, you must supply a key map to the addr_map parameter in the format {standard_key: custom_key}


.. code-block:: python

        {
            'address_line_1': 'Line1',
            'address_line_2': 'Line2',
            'city': 'City',
            'state': 'State',
            'postal_code': 'Zip'
        }


You can also customize the address constants used by setting up an `address_constants.yaml` config file.
Allowed keys are::
            DIRECTIONAL_REPLACEMENTS
            OCCUPANCY_TYPE_ABBREVIATIONS
            STATE_ABBREVIATIONS
            STREET_TYPE_ABBREVIATIONS
            KNOWN_ODDITIES
            PROBLEM_ST_TYPE_ABBRVS

You may also use the key `insertion_method` with a value of `update` or `replace` to indicate where you would like to insert your values into the existing constants or replace them. If `insertion_method` is not present, update is assumed.


.. code-block:: yaml

        insertion_method: update
        KNOWN_ODDITIES:
            'developed by HOST': ''
            ', UN ': ' UNIT '

        OCCUPANCY_TYPE_ABBREVIATIONS:
            'UN': 'UNIT'


get_geocoder_normalized_addr() uses geocoder.google to parse your address into a standard dict.  No additional cleaning is performed, so if your address contains any stray or non-conforming elements (ie: 8888 NE KILLINGSWORTH ST, UN C, PORTLAND, OR 97008), no result will be returned.
Since geocoder accepts an address string, if your address is in dict format you will need to supply a list of the address related keys within your dict, in the order of address string composition, if your keys do not match the standard key set (address_line_1, address_line_2, city, state, postal_code)

Installation
------------


``pip install usaddress-scourgify``

To use a custom constants yaml, set the ADDRESS_CONFIG_DIR environment variable with the full path to the directory containing your address_constants.yaml file

``export ADDRESS_CONFIG_DIR=/path/to/your/config_dir``

To use get_geocoder_normalized_addr, set the GOOGLE_API_KEY environment variable

``export GOOGLE_API_KEY=your_google_api_key``

Contributing
------------

License
-------
usaddress-scourgify is released under the terms of the MIT license. Full details in LICENSE file.

Changelog
---------
usaddress-scourgify was developed for use in the greenbuildingregistry project.
For a full changelog see `CHANGELOG.rst <https://github.com/GreenBuildingRegistry/usaddress-scourgify/blob/master/CHANGELOG.rst>`_.