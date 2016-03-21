#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A parser for OpenStreetMap XML data file. The first argument of the script is the path to file.
"""
import re
from collections import defaultdict

# try:
import xml.etree.cElementTree as ElementTree
# except ImportError:
#     import xml.etree.ElementTree as ElementTree

import pprint
import sys
import dateutil.parser


class SkipItem(Exception):
    pass


class MyPrettyPrinter(pprint.PrettyPrinter):
    def format(self, object, context, maxlevels, level):
        if isinstance(object, unicode):
            return (object.encode('utf8'), True, False)
        return pprint.PrettyPrinter.format(self, object, context, maxlevels, level)


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
wrong_postcodes = defaultdict(int)
saved_bul = {}
saved_str = {}
saved_pl = {}

fixme_codes = 0

# Regular expressions for scanning the <tag> elements for correct keys
lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@,\. \t\r\n]')

street_prefixes = [
    unicode("бул", "utf-8"),
    unicode("ул", "utf-8"),
    unicode("пл", "utf-8"),
]

street_prefix_regex = re.compile('(' + "|".join(street_prefixes) + ')(\s\.|\.\s|\.|\s)(?=\S)',
                                 re.UNICODE | re.IGNORECASE)


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
    skipped_items = 0
    for _, elem in ElementTree.iterparse(filename, events=('start',)):

        if elem.tag in COLLECTED_ITEMS:
            try:
                data.append(parse_element(elem))
            except SkipItem:
                skipped_items += 1
        elem.clear()  # discard the element

    print "Skipped items: {}".format(skipped_items)
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


def parse_postcode(code):
    global fixme_codes
    try:
        numeric = int(code)

        if 1000 <= numeric < 2000:
            return numeric
        else:
            raise SkipItem
    except ValueError:
        if code == "FIXME" or code == "fixme":
            fixme_codes += 1
            return None
        else:
            raise SkipItem


def add_address_value(item, field, value):
    if value is None:
        return
    if "address" not in item:
        item["address"] = {}
    item["address"][field] = value


address_types = defaultdict(int)
street_names = defaultdict(int)

lowered_street_names = defaultdict(int)


def parse_element(element):
    for attrib in element.attrib:
        if attrib not in element_fields:
            element_fields.append(attrib)

    item = {
        "id": element.attrib.get("id"),
        "user": parse_user(element),
        "timestamp": dateutil.parser.parse(parse_common_field(element, "timestamp")),
        "changeset": parse_common_field(element, "changeset"),
        "version": parse_common_field(element, "version"),
        "type": element.tag
    }

    if element.tag in POSITIONED_ITEMS:
        item["location"] = parse_location(element)

    if element.tag in REFERENCE_ITEMS:
        item["node_refs"] = parse_node_refs(element)

    for sub_tag in element:
        if sub_tag.tag == "tag":
            if sub_tag.attrib["k"] == "amenity":
                item["amenity"] = sub_tag.attrib["v"].strip()
            # Collect addresses
            elif sub_tag.attrib["k"].startswith("addr:"):
                split = sub_tag.attrib["k"].split(":")
                if len(split) == 2:
                    if split[1] == "postcode":
                        add_address_value(item, "postcode", parse_postcode(sub_tag.attrib["v"]))
                    elif split[1] == "street" and not skip_street(sub_tag.attrib["v"]):
                        correct_name = correct_street_name(sub_tag.attrib["v"])
                        street_names[correct_name] += 1
                        lowered_street_names[correct_name.lower()] += 1
                        add_address_value(item, "street", correct_name)
                        if correct_name.startswith(unicode("бул. ", "utf-8")):
                            saved_bul[correct_name.replace(unicode("бул. ", "utf-8"), "").lower()] = correct_name
                        elif correct_name.startswith(unicode("ул. ", "utf-8")):
                            saved_str[correct_name.replace(unicode("ул. ", "utf-8"), "").lower()] = correct_name
                        elif correct_name.startswith(unicode("пл. ", "utf-8")):
                            saved_pl[correct_name.replace(unicode("пл. ", "utf-8"), "").lower()] = correct_name
                    elif split[1] == "suburb":
                        add_address_value(item, "suburb", sub_tag.attrib["v"].strip())

                    address_types[split[1]] += 1
            elif sub_tag.attrib["k"] == "name":
                item["name"] = sub_tag.attrib["v"].strip()

    # scan_tags(element)

    return item


def sort_dict(d):
    return sorted(d.items(), key=lambda x: x[1], reverse=True)


def skip_street(orig_street_name):
    manually_skipped_streets = [
        "no",
        "apartments",
        "c",
        "Tietotie"
    ]
    return orig_street_name.startswith("http") or orig_street_name.startswith(
        unicode("жк.", "utf-8")) or orig_street_name in manually_skipped_streets


manually_corrected_names = [
    "ул. Ген. Йосиф В. Гурко",
    "бул. Ген. Тотлебен",
    "бул. Цариградско шосе",
    "бул. Черни връх",
    "ул. Магнаурска школа",
    "ул. Стара планина",
    "бул. Витоша",
    "Цар Борис III",
    "Родопски извор",
    "Гоце Делчев",
    "Три уши",
    "Връх Манчо",
    "Черни връх",
    "Детелин войвода"
]

manual_street_names_ref = {}


for name in manually_corrected_names:
    manual_street_names_ref[unicode(name, "utf-8").lower()] = unicode(name, "utf-8")

manually_translated_streets = {
    'Andrey Saharov Blvd': "Андрей Сахаров",
    'Atanas Kirchev': "Атанас Кирчев",
    'Boulevard Iskarsko Shose': "Искърско шосе",
    'Gen. Asen Nikolov': "Ген. Асен Николов",
    'Georgi S. Rakovski': "Георги С. Раковски",
    'Golyama mogila street': "Голяма Могила",
    'Gotse Delchev': "Гоце Делчев",
    'Kumata 1': "Кумата",
    'Madara': "Мадара",
    'Metodi Popov Str.': "Методи Попов",
    'Nikola Gabrovski': "Никола Габровски",
    'Panayot Volov': "Панайот Волов",
    'Pyrwa': "Първа Българска армия",
    'Slavyanska': "Славянска",
    'Srebarna': "Сребърна",
    'Tsarigradsko Chausse Blvd': "Цариградско шосе",
    'bul.Tzar Boris III': "Цар Борис III",
    u'\u0426\u0430\u0440 \u0411\u043e\u0440\u0438\u0441 \u0406\u0406\u0406': "Цар Борис III"
}


def correct_street_name(str_name):
    bad_chars = [
        unicode("'", "utf-8"),
        unicode('"', "utf-8"),
        unicode('”', "utf-8"),
        unicode('„', "utf-8"),
        unicode('“', "utf-8")
    ]
    # Clean leading/trailing whitespaces and quotes
    str_name = re.sub('[\'"' + "".join(bad_chars) + ']', '', str_name.strip())

    if str_name.startswith(unicode("улица", "utf-8")):
        str_name = str_name.replace(unicode("улица", "utf-8"), unicode("ул.", "utf-8"))
    if str_name.startswith(unicode("булевард", "utf-8")):
        str_name = str_name.replace(unicode("булевард", "utf-8"), unicode("бул.", "utf-8"))
    if str_name.startswith(unicode("площад", "utf-8")):
        str_name = str_name.replace(unicode("площад", "utf-8"), unicode("пл.", "utf-8"))

    if str_name.lower() in manual_street_names_ref:
        return manual_street_names_ref[str_name.lower()]
    elif str_name in manually_translated_streets:
        return unicode(manually_translated_streets[str_name], "utf-8")
    else:
        return street_prefix_regex.sub(lambda m: m.group(1).lower() + ". ", str_name)


def add_record(db, record):
    # Changes to this function will be reflected in the output.
    # All other functions are for local use only.
    # Try changing the name of the city to be inserted
    db.osm_data.insert(record)


def get_db():
    # For local use
    from pymongo import MongoClient
    client = MongoClient('localhost:27017')
    # 'examples' here is the database name. It will be created if it does not exist.
    db = client.project3
    return db

if __name__ == "__main__":
    processed_data = parse_file(sys.argv[1])

    # print "Missing user data:"
    # pprint.pprint(missing_user_data)
    # print "Missing location data:"
    # pprint.pprint(missing_location_data)
    # print "Missing common fields"
    # pprint.pprint(missing_common_fields)
    # print "Possible element fields:"
    # pprint.pprint(element_fields)
    # print "Colon <tag> keys:"
    # pprint.pprint(sort_dict(colon_tag_keys))
    # print "Problem <tag> keys:"
    # pprint.pprint(sort_dict(problem_tag_keys))
    # print "Unmatched <tag> keys:"
    # pprint.pprint(sort_dict(unmatched_tag_keys))
    # print "Address types"
    # pprint.pprint(dict(address_types))
    # print "Wrong postcodes"
    # pprint.pprint(dict(wrong_postcodes))
    # print "FIXME codes: {}".format(fixme_codes)
    # print "Street names"
    # MyPrettyPrinter().pprint(dict(lowered_street_names))
    # for street_name in street_names:
    #     if street_names[street_name] != lowered_street_names[street_name.lower()]:
    #         print street_name
    # MyPrettyPrinter().pprint(dict(street_names))
    unfinished_streets = defaultdict(int)
    db = get_db()
    for entry in processed_data:
        if "address" in entry:
            if "street" in entry["address"]:
                street_name = entry["address"]["street"]
                if (not street_name.startswith(unicode("ул.", "utf-8"))) and \
                        (not street_name.startswith(unicode("бул.", "utf-8"))) and \
                        (not street_name.startswith(unicode("пл.", "utf-8"))):
                    street_name_lower = street_name.lower()
                    if street_name_lower in saved_bul:
                        entry["address"]["street"] = saved_bul[street_name_lower]
                    elif street_name_lower in saved_str:
                        entry["address"]["street"] = saved_str[street_name_lower]
                    elif street_name_lower in saved_pl:
                        entry["address"]["street"] = saved_pl[street_name_lower]
                    else:
                        entry["address"]["street"] = unicode("ул. ", "utf-8") + street_name

        add_record(db, entry)

    # MyPrettyPrinter().pprint(dict(unfinished_streets))
    # MyPrettyPrinter().pprint(saved_str)
    # MyPrettyPrinter().pprint(saved_str)
    # MyPrettyPrinter().pprint(saved_pl)
    # print lowered_street_names



    # import json
    # with open('data.json', 'w') as outfile:
    #     json.dump(processed_data, outfile)