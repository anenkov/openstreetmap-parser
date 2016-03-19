#!/usr/bin/env python
# -*- coding: utf-8 -*-
import xml.etree.cElementTree as ET
import pprint
import re
import codecs
import json

"""
Wrangle the data and transform the shape of the data
into the model we mentioned earlier. The output should be a list of dictionaries
that look like this:

"""

lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

CREATED = ["version", "changeset", "timestamp", "user", "uid"]


def shape_element(element):
    node = {}
    if element.tag == "node" or element.tag == "way":
        # YOUR CODE HERE
        node['id'] = element.attrib.get("id")
        node['type'] = element.tag
        node['visible'] = element.attrib.get("visible")
        node['created'] = {}
        node['created']['version'] = element.attrib.get("version")
        node['created']['changeset'] = element.attrib.get("changeset")
        node['created']['timestamp'] = element.attrib.get("timestamp")
        node['created']['user'] = element.attrib.get("user")
        node['created']['uid'] = element.attrib.get("uid")
        if element.tag == "node":
            node['pos'] = []
            node['pos'].append(float(element.attrib.get("lat")))
            node['pos'].append(float(element.attrib.get("lon")))
        elif element.tag == 'way':
            node['node_refs'] = []

        for sub_tag in element:
            if sub_tag.tag == 'tag':
                if lower.search(sub_tag.attrib['k']):
                    node[sub_tag.attrib['k']] = sub_tag.attrib['v']
                elif lower_colon.search(sub_tag.attrib['k']):
                    if sub_tag.attrib['k'].startswith('addr:'):
                        split_addr = sub_tag.attrib['k'].split(":")
                        if len(split_addr) == 2:
                            if 'address' not in node:
                                node['address'] = {}
                            node['address'][split_addr[1]] = sub_tag.attrib['v']
            elif sub_tag.tag == 'nd':
                node['node_refs'].append(sub_tag.attrib['ref'])
        return node
    else:
        return None


def process_map(file_in, pretty=False):
    # You do not need to change this file
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w") as fo:
        for _, element in ET.iterparse(file_in):
            el = shape_element(element)
            if el:
                data.append(el)
                if pretty:
                    fo.write(json.dumps(el, indent=2) + "\n")
                else:
                    fo.write(json.dumps(el) + "\n")
    return data


def test():
    # NOTE: if you are running this code on your computer, with a larger dataset,
    # call the process_map procedure with pretty=False. The pretty=True option adds
    # additional spaces to the output, making it significantly larger.
    data = process_map('example.osm', True)
    # pprint.pprint(data)

    correct_first_elem = {
        "id": "261114295",
        "visible": "true",
        "type": "node",
        "pos": [41.9730791, -87.6866303],
        "created": {
            "changeset": "11129782",
            "user": "bbmiller",
            "version": "7",
            "uid": "451048",
            "timestamp": "2012-03-28T18:31:23Z"
        }
    }
    assert data[0] == correct_first_elem
    assert data[-1]["address"] == {
        "street": "West Lexington St.",
        "housenumber": "1412"
    }
    assert data[-1]["node_refs"] == ["2199822281", "2199822390", "2199822392", "2199822369",
                                     "2199822370", "2199822284", "2199822281"]


if __name__ == "__main__":
    test()
