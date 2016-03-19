#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A parser for XML data file. The first argument of the script is the path to file.
The parser counts number of occurences for each tag, so user will be able to determine the size of the document
"""
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import pprint
from collections import defaultdict

import sys

FILE_PATH = "example.osm"


def count_tags(filename):
    tags = defaultdict(int)

    for event, elem in ET.iterparse(filename):
        if event == 'end':
            tags[elem.tag] += 1
        elem.clear()  # discard the element

    return tags


def test():
    tags = count_tags(FILE_PATH)
    pprint.pprint(tags)
    assert tags == {'bounds': 1,
                    'member': 3,
                    'nd': 4,
                    'node': 20,
                    'osm': 1,
                    'relation': 1,
                    'tag': 7,
                    'way': 1}


if __name__ == "__main__":
    test()
    #print count_tags(sys.argv[1])

