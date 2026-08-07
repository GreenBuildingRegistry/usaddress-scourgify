usaddress-scourgify
===================

A Python3.x library for cleaning/normalizing US addresses following USPS pub 28 and RESO guidelines.



Documentation
-------------
Use

``normalize_address_record()``

 or

``get_geocoder_normalized_addr()``

or

``NormalizeAddress().normalize()``

to standardize your addresses. (Note: usaddress-scourgify does not make any attempts at address validation.)

Both functions, and the class init, take an address string, or a dict-like object, and return an address dict with all field values in uppercase format mapped to the keys address_line_1, address_line_2, city, state, postal_code...


.. code-block:: python


        from scourgify import normalize_address_record, NormalizeAddress

        normalize_address_record('123 southwest Main street, Boring, or, 97203')
        
        normalize_address_record({
            'address_line_1': '123 southwest Main street',
            'address_line_2': 'unit 2',
            'city': 'Boring',
            'state': 'or',
            'postal_code': '97203'
        })

        NormalizeAddress('123 southwest Main street, Boring, or, 97203').normalize()

expected output


.. code-block:: python

       {
            'address_line_1': '123 SW MAIN ST',
            'address_line_2': 'UNIT 2'
            'city': 'BORING',
            'state': 'OR',
            'postal_code': '97203'
        }


By default, the output style abbreviates all pre or post directionals, street types, and occupancy types.
Alternately, if you would like to receive your output with full word directionals and street types, you can use the `long_hand` parameter.

.. code-block:: python


        from scourgify import normalize_address_record, NormalizeAddress

        normalize_address_record('123 southwest Main street, Boring, or, 97203', long_hand=True)

        normalize_address_record({
            'address_line_1': '123 southwest Main street',
            'address_line_2': 'unit 2,
            'city': 'Boring',
            'state': 'or',
            'postal_code': '97203'
        })

        NormalizeAddress('123 southwest Main street, Boring, or, 97203', long_hand=True).normalize()

expected output


.. code-block:: python

       {
            'address_line_1': '123 SOUTHWEST MAIN STREET',
            'address_line_2': 'UNIT 2'
            'city': 'BORING',
            'state': 'OR',
            'postal_code': '97203'
        }

normalized_address_record() uses the included processing functions to remove unacceptable special characters, extra spaces, predictable abnormal character sub-strings and phrases. It also abbreviates directional indicators and street types according to the abbreviation mappings found in address_constants.  If applicable, line 2 address elements (ie: Apt, Unit) are separated from line 1 inputs and standard occupancy type abbreviations are applied.

You may supply additional additional processing functions as a list of callable supplied to the addtl_funcs parameter. Any additional functions should take a string address and return a tuple of strings (line1, line2).

Postal codes are normalized to US zip or zip+4 and zero padded as applicable.  ie: `2129 => 02129`, `02129-44 => 02129-0044`, `021290044 => 02129-0044`.
However, postal codes that cannot be effectively normalized, such as invalid length or invalid characters, will raise AddressValidationError. ie `12345678901 or 02129- or 02129-0044-123, etc`

Alternately, you may extend the `NormalizeAddress` class to customize the normalization behavior by overriding any of the class' methods.

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


Multi-word street names:
~~~~~~~~~~~~~~~~~~~~~~~~

There is a known issue with some multi-word street names, or city names that are also a steet type, (EG: '1111 Via Christina, Vista, CA 92084' or '9999 LA TORTOLA SAN DIEGO CA 92129') when parsing addresses as a single string.
Because of the complexity of parsing these address types, the base package, `usaddress` sometimes misidentifies the city as part of the street name, or the street name as part of the city.
The only current solution is to identify the city for prior to normalization, which means having to first break your single string into and address dict.

Examples as single line:
.. code-block:: python

    addr = '9999 LA TORTOLA SAN DIEGO CA 92129'
    {
        'address_line_1': '12790 LA',
        'address_line_2': None,
        'city': 'TORTOLA SAN DIEGO',
        'state': 'CA',
        'postal_code': '92129'
    }

    addr = "1509 Via Christina, Vista, CA 92084"
    {
      "address_line_1": "1509 VIA CHRISTINA VIS",
      "address_line_2": null,
      "city": null,
      "state": "CA",
      "postal_code": "92084"
    }


Versus examples as addr dict:
.. code-block:: python

    addr = {
        'address_line_1': '12790 LA TORTOLA',
        'city': 'SAN DIEGO',
        'state': 'CA',
        'postal_code': '92129'
    }
    OrderedDict([('address_line_1', '9999 LA TORTOLA'),
             ('address_line_2', None),
             ('city', 'SAN DIEGO'),
             ('state', 'CA'),
             ('postal_code', '92129')])


    addr = {
      "address_line_1": "1509 Via Christina",
      "city": 'Vista',
      "state": "CA",
      "postal_code": "92084"
    }
    OrderedDict([('address_line_1', '1509 VIA CHRISTINA'),
             ('address_line_2', None),
             ('city', 'VISTA'),
             ('state', 'CA'),
             ('postal_code', '92084')])


Installation
------------
Requires Python3.x.

``pip install usaddress-scourgify``

To use a custom constants yaml, set the ADDRESS_CONFIG_DIR environment variable with the full path to the directory containing your address_constants.yaml file

``export ADDRESS_CONFIG_DIR=/path/to/your/config_dir``

To use get_geocoder_normalized_addr, set the GOOGLE_API_KEY environment variable

``export GOOGLE_API_KEY=your_google_api_key``

Contributing
------------
Create a new branch to hold your change; no pull requests submitted directly to dev or master will be approved.  Please include a comment explain the issue your pull request solves. Make sure all appropriate test, and tox, updates are included and that all tests are passing.

License
-------
usaddress-scourgify is released under the terms of the MIT license. Full details in LICENSE file.

Changelog
---------
usaddress-scourgify was developed for use in the greenbuildingregistry project.
For a full changelog see `CHANGELOG.rst <https://github.com/GreenBuildingRegistry/usaddress-scourgify/blob/master/CHANGELOG.rst>`_.
