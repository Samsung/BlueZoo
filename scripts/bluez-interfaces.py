#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import re
from argparse import ArgumentParser
from pathlib import Path
from xml.etree import ElementTree as ET

import pyparsing as pp

ARRAY = pp.Forward()
TYPE = (ARRAY | pp.Word(pp.alphas, pp.alphas + pp.nums + "_"))("type")
IDENTIFIER = pp.Word(pp.alphas, pp.alphas + pp.nums + "_")("name")
ARRAY << pp.Group(
    pp.Keyword("array")
    + pp.Literal("{").suppress()
    + pp.delimitedList(pp.Group(TYPE + pp.Optional(IDENTIFIER)))("elements")
    + pp.Literal("}").suppress()
)
PARAM = pp.Group(TYPE + pp.Optional(IDENTIFIER))("param")
ANNOTATIONS = (
    pp.Literal("[").suppress()
    + pp.delimitedList(pp.Word(pp.alphas, pp.alphas + pp.nums + "-"))
    + pp.Literal("]").suppress()
)("annotations")
INTERFACE = pp.Word(pp.alphas, pp.alphas + pp.nums + ".")("name") + pp.Optional(
    ANNOTATIONS
)
METHOD = (
    pp.Group(pp.delimitedList(TYPE))("returns")
    + IDENTIFIER
    + pp.Literal("(").suppress()
    + pp.Optional(pp.Group(pp.delimitedList(PARAM))("args"))
    + pp.Literal(")").suppress()
    + pp.Optional(ANNOTATIONS)
)
PROPERTY = TYPE + IDENTIFIER + pp.Optional(ANNOTATIONS)


TYPES = {
    "bool": "b",
    "boolean": "b",
    "byte": "y",
    "dict": "a{sv}",
    "double": "d",
    "fd": "h",
    "int16": "n",
    "int32": "i",
    "int64": "x",
    "object": "o",
    "objects": "a{oa{sv}}",
    "properties": "a{sa{sv}}",
    "signature": "g",
    "string": "s",
    "uint16_t": "q",
    "uint16": "q",
    "uint32": "u",
    "uint64": "t",
    "variant": "v",
    "void": None,
}


def type2signature(t):
    """Convert a parsed type to a D-Bus signature."""
    if isinstance(t, str):
        return TYPES[t]
    if t[0] == "array":
        types = [type2signature(e.type) for e in t.elements]
        return f"a{''.join(types)}"
    raise ValueError(f"Unknown type: {t}")


ANNOTATIONS = {
    "deprecated": "org.freedesktop.DBus.Deprecated",
    "experimental": "org.freedesktop.DBus.Experimental",
    "noreply": "org.freedesktop.DBus.Method.NoReply",
    "optional": "org.freedesktop.DBus.Optional",
    "adapter-only": "org.bluez.AdapterOnly",
    "device-only": "org.bluez.DeviceOnly",
}


def annotate(element: ET.Element, annotation):
    """Annotate an XML element with annotations."""
    annotation = annotation.lower()
    if annotation in ("readonly", "read-only"):
        element.set("access", "read")
    elif annotation in ("readwrite", "read-write"):
        element.set("access", "readwrite")
    elif annotation in ("writeonly", "write-only"):
        element.set("access", "write")
    else:
        ET.SubElement(element, "annotation", name=ANNOTATIONS[annotation], value="true")


def comment(parent: ET.Element, text: str):
    """Prepend a comment to the last child of an XML element."""
    if len(parent) == 1 or parent[-2].tag != ET.Comment:
        parent.insert(-1, ET.Comment(""))
    current = parent[-2].text.strip().split()
    current.extend(text.strip().split())
    parent[-2].text = " " + " ".join(current) + " "


def save(node, name):
    """Save an XML node element to a file."""
    node.set("xmlns:doc", "http://www.freedesktop.org/dbus/1.0/doc.dtd")
    ET.indent(node, space="\t", level=0)
    ET.ElementTree(node).write(str(name))


parser = ArgumentParser(description="Extract D-Bus API from BlueZ documentation")
parser.add_argument("-l", "--list", action="store_true", help="list interfaces")
parser.add_argument("-o", "--output-dir", metavar="DIR", type=Path, default=Path("."),
                    help="output directory")
parser.add_argument("--output-file", metavar="FILE", type=Path,
                    help="combine all interfaces into a single XML file")
parser.add_argument("inputs", metavar="INPUT", type=Path, nargs="+",
                    help="input file(s)")

args = parser.parse_args()

re_interface = re.compile(r"^Interface$")
re_methods = re.compile(r"^Methods$")
re_properties = re.compile(r"^Properties$")

re_service = re.compile(r":Service:\s+(.+)")
re_interface = re.compile(r":Interface:\s+(.+)")
re_object_path = re.compile(r":Object path:\s+(.+)")
re_method = re.compile(r"([\w\{\}, ]+)\s+(\w+)\((.*?)?\)(\s+\[(.+)\])?")
re_property = re.compile(r"([\w\{\}]+)\s+(\w+)(\s+\[(.+)\])")

interfaces = []
for name in args.inputs:
    with name.open() as f:
        lines = f.readlines()

    section = None
    paragraph = 0
    interface = ET.Element("interface")
    interfaces.append(interface)
    for line in lines:
        if not line.strip():
            paragraph += 1
            continue

        if m := re_interface.match(line):
            section = "interface"
        elif m := re_methods.match(line):
            section = "methods"
        elif m := re_properties.match(line):
            section = "properties"

        if section == "interface":
            if m := re_service.match(line):
                service = m.group(1)
            if m := re_interface.match(line):
                ast = INTERFACE.parseString(m.group(1))
                interface.set("name", ast.name)
                for x in ast.annotations:
                    annotate(interface, x)
            if m := re_object_path.match(line):
                object_path = m.group(1)
        elif section == "methods":
            if re_method.match(line):
                paragraph = 0
                ast = METHOD.parseString(line)
                elem = ET.SubElement(interface, "method", name=ast.name)
                for i, t in enumerate(ast.returns):
                    if s := type2signature(t):
                        ET.SubElement(
                            elem, "arg", direction="out", name=f"r{i}", type=s
                        )
                for x in ast.args:
                    if s := type2signature(x.type):
                        ET.SubElement(elem, "arg", direction="in", name=x.name, type=s)
                for x in ast.annotations:
                    annotate(elem, x)
            elif paragraph == 1:
                comment(interface, line)
        elif section == "properties":
            if re_property.match(line):
                paragraph = 0
                ast = PROPERTY.parseString(line)
                elem = ET.SubElement(
                    interface, "property", name=ast.name, type=type2signature(ast.type)
                )
                for x in ast.annotations:
                    annotate(elem, x)
            elif paragraph == 1:
                comment(interface, line)

if args.list:
    for interface in interfaces:
        print(interface.get("name"))
    exit()

if args.output_file:
    root = ET.Element("node")
    for interface in interfaces:
        root.append(interface)
    save(root, args.output_file)
    exit()

for interface in interfaces:
    root = ET.Element("node")
    root.append(interface)
    print(f"Writing {interface.get('name')}.xml")
    save(root, args.output_dir / f"{interface.get('name')}.xml")
