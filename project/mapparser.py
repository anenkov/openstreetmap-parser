#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A parser for OpenStreetMap XML data file. The first argument of the script is the path to file.
"""
import re
from collections import defaultdict

try:
    import xml.etree.cElementTree as ElementTree
except ImportError:
    import xml.etree.ElementTree as ElementTree

import pprint
import sys

# Tags we're interested in collecting
COLLECTED_ITEMS = ["node", "way"]

# Tags for which we get the location
POSITIONED_ITEMS = ["node"]

# Tags for which we collect node references
REFERENCE_ITEMS = ["way"]

missing_user_data = {
    "username": 0,
    "uid": 0
}

missing_location_data = {
    "lat": 0,
    "lon": 0,
    "node": 0,
    "way": 0
}

missing_common_fields = {
    "version": 0,
    "timestamp": 0,
    "changeset": 0
}

element_fields = []

colon_tag_keys = defaultdict(int)
problem_tag_keys = defaultdict(int)
unmatched_tag_keys = defaultdict(int)

# Regular expressions for scanning the <tag> elements for correct keys
lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@,\. \t\r\n]')


def parse_user(element):
    user_name = element.attrib.get("user")
    user_id = element.attrib.get("uid")

    if user_name is None:
        missing_user_data["username"] += 1

    if user_id is None:
        missing_user_data["uid"] += 1

    return {"name": user_name, "id": user_id}


def parse_location(element):
    lat = element.attrib.get("lat")
    lon = element.attrib.get("lon")

    if lat is None:
        missing_location_data["lat"] += 1
        missing_location_data[element.tag] += 1
        return []

    if lon is None:
        missing_location_data["lon"] += 1
        return []

    return [float(lat), float(lon)]


def parse_file(filename):
    data = []
    for _, elem in ElementTree.iterparse(filename, events=('start',)):

        if elem.tag in COLLECTED_ITEMS:
            data.append(parse_element(elem))
        elem.clear()  # discard the element

    return data


def parse_common_field(element, field):
    value = element.attrib.get(field)
    if value is None:
        missing_common_fields[value] += 1

    return value


def parse_node_refs(element):
    node_refs = []
    for sub_tag in element:
        if sub_tag.tag == "nd":
            node_refs.append(sub_tag.attrib['ref'])

    return node_refs


def scan_tags(element):
    for sub_tag in element:
        if sub_tag.tag == "tag":
            tag_key = sub_tag.attrib["k"]
            if lower.search(tag_key):
                pass
            elif lower_colon.search(tag_key) is not None:
                    colon_tag_keys[tag_key] += 1
            elif problemchars.search(tag_key) is not None:
                    problem_tag_keys[tag_key] += 1
            else:
                unmatched_tag_keys[tag_key] += 1


def parse_element(element):
    for attrib in element.attrib:
        if attrib not in element_fields:
            element_fields.append(attrib)

    item = {
        "id": element.attrib.get("id"),
        "user": parse_user(element),
        "timestamp": parse_common_field(element, "timestamp"),
        "changeset": parse_common_field(element, "changeset"),
        "version": parse_common_field(element, "version"),
    }

    if element.tag in POSITIONED_ITEMS:
        item["location"] = parse_location(element)

    if element.tag in REFERENCE_ITEMS:
        item["node_refs"] = parse_node_refs(element)

    scan_tags(element)

    return item


def sort_dict(d):
    return sorted(d.items(), key=lambda x: x[1], reverse=True)

if __name__ == "__main__":
    parse_file(sys.argv[1])

    print "Missing user data:"
    pprint.pprint(missing_user_data)
    print "Missing location data:"
    pprint.pprint(missing_location_data)
    print "Missing common fields"
    pprint.pprint(missing_common_fields)
    print "Possible element fields:"
    pprint.pprint(element_fields)
    print "Colon <tag> keys:"
    pprint.pprint(sort_dict(colon_tag_keys))
    print "Problem <tag> keys:"
    pprint.pprint(sort_dict(problem_tag_keys))
    print "Unmatched <tag> keys:"
    pprint.pprint(sort_dict(unmatched_tag_keys))
