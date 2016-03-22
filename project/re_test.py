# coding=utf-8
import re


"""
A test area for regex matching of street prefixes
"""

search = [
    unicode("бул", "utf-8"),
    unicode("ул", "utf-8"),
    unicode("пл.", "utf-8"),
]

regex = re.compile('(' + "|".join(search) + ')(\s\.|\.\s|\.|\s)(?=\S)', re.UNICODE | re.IGNORECASE)
print regex.sub(lambda m: m.group(1).lower() + ". ", unicode("бул. Фрит", "utf-8"))
print regex.sub(lambda m: m.group(1).lower() + ". ", unicode("бул.Фрит", "utf-8"))
print regex.sub(lambda m: m.group(1).lower() + ". ", unicode("бул Фрит", "utf-8"))
print regex.sub(lambda m: m.group(1).lower() + ". ", unicode("Бул. Фрит", "utf-8"))
print regex.sub(lambda m: m.group(1).lower() + ". ", unicode("БУЛ.Фрит", "utf-8"))
print regex.sub(lambda m: m.group(1).lower() + ". ", unicode("ул .Солунска", "utf-8"))