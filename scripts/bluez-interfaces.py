#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import re
import sys
from argparse import ArgumentParser, FileType
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

import pyparsing as pp


@dataclass
class Method:
    name: str
    returns: list[str]
    parameters: list[tuple[str, str | pp.ParseResults]]
    annotations: set[str]
    description: str = ""
    notes: str = ""


@dataclass
class Property:
    name: str
    type: str | pp.ParseResults
    annotations: set[str]
    description: str = ""
    notes: str = ""


@dataclass
class Interface:
    name: str
    annotations: set[str]
    methods: list[Method] = field(default_factory=list)
    signals: list[Method] = field(default_factory=list)
    properties: list[Property] = field(default_factory=list)
    notes: str = ""


class BluezDocParser:
    """BlueZ documentation D-Bus API parser."""

    IDENTIFIER = pp.Word(pp.alphas, pp.alphanums + "_")("name")

    ARRAY = pp.Forward()
    # TODO: Type should not contain "_" character, however, BlueZ documentation
    #       has some inconsistencies in this regard, e.g. "uint32_t".
    TYPE = (ARRAY | pp.Word(pp.alphas, pp.alphanums + "_"))("type")

    PARAM = pp.Group(TYPE + pp.Optional(IDENTIFIER))("param")

    ARRAY <<= pp.Group(
        pp.Keyword("array")
        + pp.Literal("{").suppress()
        + pp.delimitedList(PARAM)("elements")
        + pp.Literal("}").suppress(),
    )

    ANNOTATIONS = (
        pp.Literal("[").suppress()
        + pp.delimitedList(
            # Match annotation keywords like "experimental", "ISO only", etc.
            pp.OneOrMore(pp.Word(pp.alphanums + "-/")).setParseAction(" ".join))
        + pp.Literal("]").suppress()
    )("annotations")

    NOTES = pp.Group(
        pp.Literal("(").suppress()
        + pp.CharsNotIn("()")
        + pp.Literal(")").suppress(),
    )("notes")

    INTERFACE = (
        pp.Word(pp.alphas, pp.alphanums + ".")("name")
        + pp.Optional(ANNOTATIONS)
    )

    METHOD = (
        pp.Group(pp.delimitedList(TYPE))("returns")
        + IDENTIFIER
        + pp.Literal("(").suppress()
        + pp.Optional(pp.Group(pp.delimitedList(PARAM))("parameters"))
        + pp.Literal(")").suppress()
        + pp.Optional(ANNOTATIONS)
        + pp.Optional(NOTES)
    )

    PROPERTY = (
        TYPE
        + IDENTIFIER
        + pp.Optional(ANNOTATIONS)
        + pp.Optional(NOTES)
    )

    @classmethod
    def parseAnnotations(cls, annotations):
        """Convert parsed annotations to a set of annotation tags."""
        tags = set()
        for token in annotations:
            token = token.lower()
            if token == "required":
                # Everything is required by default, so we can skip this.
                continue
            if token in ("read-only", "readonly"):
                tags.add("read")
            elif token in ("readwrite", "read-write", "read/write"):
                tags.update(("read", "write"))
            elif token in ("writeonly", "write-only"):
                tags.add("write")
            else:
                tags.add(token)
        return tags

    @classmethod
    def parseInterface(cls, string: str):
        ast = cls.INTERFACE.parseString(string, parseAll=True)
        return Interface(
            name=str(ast.name),
            annotations=cls.parseAnnotations(ast.annotations),
        )

    @classmethod
    def parseMethod(cls, string: str):
        ast = cls.METHOD.parseString(string, parseAll=True)
        return Method(
            name=str(ast.name),
            returns=[x for x in ast.returns if x],
            parameters=[(x.name, x.type) for x in ast.parameters],
            annotations=cls.parseAnnotations(ast.annotations),
        )

    @classmethod
    def parseProperty(cls, string: str):
        # TODO: Enable parseAll=True after fixing the documentation.
        ast = cls.PROPERTY.parseString(string, parseAll=False)
        return Property(
            name=str(ast.name),
            type=ast.type,
            annotations=cls.parseAnnotations(ast.annotations),
        )


def type2python(t):
    """Convert a parsed type to a Python type."""
    if t == "void":
        return "None"
    if t in ["bool", "boolean"]:
        return "bool"
    if t in ["signature", "object", "string"]:
        return "str"
    if t in ["fd", "byte", "int16", "int16_t", "int32", "int32_t", "int64", "int64_t",
             "uint16", "uint16_t", "uint32", "uint32_t", "uint64", "uint64_t"]:
        return "int"
    if t == "double":
        return "float"
    if t == "dict":
        return "dict[str, tuple[str, object]]"
    if t == "variant":
        return "tuple[str, object]"
    if t == "properties":
        return "dict[str, dict[str, object]]"
    if t == "objects":
        # TODO: Check if this is not a typo in the documentation.
        return "dict[str, dict[str, object]]"
    if t[0] == "array":
        if len(t.elements) == 1 and t.elements[0].type == "byte":
            return "bytes"
        types = [type2python(e.type) for e in t.elements]
        if len(types) == 1:
            return f"list[{types[0]}]"
        return f"tuple[{''.join(types)}]"
    msg = f"Unknown type: {t}"
    raise ValueError(msg)


# Types used in BlueZ documentation and their D-Bus signatures.
TYPES = {
    "bool": "b",
    "boolean": "b",
    "byte": "y",
    "dict": "a{sv}",
    "double": "d",
    "fd": "h",
    "int16": "n",
    "int16_t": "n",
    "int32": "i",
    "int32_t": "i",
    "int64": "x",
    "int64_t": "x",
    "object": "o",
    "objects": "a{oa{sv}}",
    "properties": "a{sa{sv}}",
    "signature": "g",
    "string": "s",
    "uint16": "q",
    "uint16_t": "q",
    "uint32": "u",
    "uint32_t": "u",
    "uint64": "t",
    "uint64_t": "t",
    "variant": "v",
    "void": None,
}


def type2signature(t):
    """Convert a parsed type to a D-Bus signature."""
    if isinstance(t, str):
        return TYPES[t]
    if t[0] == "array":
        types = [type2signature(e.type) for e in t.elements]
        if len(types) == 1:
            return f"a{types[0]}"
        return f"a({''.join(types)})"
    msg = f"Unknown type: {t}"
    raise ValueError(msg)


def list2python(lst):
    """Stringify a list to a Python code."""
    return repr(lst).replace("'", '"')


# Annotations used in BlueZ documentation and their D-Bus equivalents.
ANNOTATIONS = {
    "deprecated": "org.freedesktop.DBus.Deprecated",
    "experimental": "org.freedesktop.DBus.Experimental",
    "noreply": "org.freedesktop.DBus.Method.NoReply",
    "optional": "org.freedesktop.DBus.Optional",
    "adapter-only": "org.bluez.AdapterOnly",
    "device-only": "org.bluez.DeviceOnly",
    "iso only": "org.bluez.ISOOnly",
    "cis only": "org.bluez.CISOnly",
    "bis only": "org.bluez.BISOnly",
}


def annotate(element: ET.Element, annotations: set[str]):
    """Annotate an XML element with annotations."""
    if {"read", "write"} <= annotations:
        element.set("access", "readwrite")
    elif "read" in annotations:
        element.set("access", "read")
    elif "write" in annotations:
        element.set("access", "write")
    for tag in annotations - {"read", "write"}:
        ET.SubElement(element, "annotation",
                      name=ANNOTATIONS[tag],
                      value="true")


def comment(parent: ET.Element, text: str):
    """Prepend a comment to the last child of an XML element."""
    if len(parent) == 1 or parent[-2].tag != ET.Comment:
        parent.insert(-1, ET.Comment(""))
    current = (parent[-2].text or "").strip().split()
    current.extend(text.strip().split())
    parent[-2].text = " " + " ".join(current) + " "


parser = ArgumentParser(description="Extract D-Bus API from BlueZ documentation")
parser.add_argument("-v", "--verbose", action="store_true", help="show verbose output")
parser.add_argument("-l", "--list", action="store_true", help="list all extracted interfaces")
parser.add_argument("-o", "--output-dir", metavar="DIR", type=Path, default=Path("."),
                    help="output directory")
parser.add_argument("--save-xml", action="store_true", help="save XML files")
parser.add_argument("sources", metavar="FILE", type=FileType("r"), nargs="+",
                    help="input file(s)")

args = parser.parse_args()

re_section_interface = re.compile(r"^Interface$")
re_section_methods = re.compile(r"^Methods$")
re_section_signals = re.compile(r"^Signals$")
re_section_properties = re.compile(r"^(MediaEndpoint )?Properties$")

re_service = re.compile(r":Service:\s+(.+)")
re_interface = re.compile(r":Interface:\s+(.+)")
re_object_path = re.compile(r":Object path:\s+(.+)")
re_method = re.compile(r"([\w\{\}, ]+)\s+(\w+)\((.*?)?\)(\s+\[(.+)\])?")
re_property = re.compile(r"([\w\{\}]+)\s+(\w+)(\s+\[(.+)\])")

interfaces = []
for source in args.sources:
    if args.verbose:
        print(f"Parsing {source.name}")

    with source as f:
        lines = f.readlines()

    paragraph = 0
    section = None
    for i, line in enumerate(lines):
        if not line.strip():
            paragraph += 1
            continue

        if m := re_section_interface.match(line):
            section = "interface"
        elif m := re_section_methods.match(line):
            section = "methods"
        elif m := re_section_signals.match(line):
            section = "signals"
        elif m := re_section_properties.match(line):
            section = "properties"

        header = False
        # Check if the current line is marked as a header.
        with suppress(IndexError):
            header = lines[i + 1].startswith("````")

        if section == "interface":
            if m := re_service.match(line):
                service = m.group(1)
            if m := re_interface.match(line):
                interface = BluezDocParser.parseInterface(m.group(1))
            if m := re_object_path.match(line):
                object_path = m.group(1)
        elif section == "methods":
            if header and re_method.match(line):
                method = BluezDocParser.parseMethod(line)
                if method.name not in [x.name for x in interface.methods]:
                    interface.methods.append(method)
                    paragraph = 0
            elif paragraph == 1:
                method.description += line
        elif section == "signals":
            # Signals are similar to methods but without return values.
            if header and re_method.match(line):
                signal = BluezDocParser.parseMethod(line)
                if signal.name not in [x.name for x in interface.signals]:
                    interface.signals.append(signal)
                    paragraph = 0
            elif paragraph == 1:
                signal.description += line
        elif section == "properties":
            if header and re_property.match(line):
                prop = BluezDocParser.parseProperty(line)
                if prop.name not in [x.name for x in interface.properties]:
                    interface.properties.append(prop)
                    paragraph = 0
            elif paragraph == 1:
                prop.description += line

    interfaces.append(interface)

if args.list:
    for iface in interfaces:
        print(iface.name)
    sys.exit()

TEMPLATE_HEADER = """
# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only
#
# This file is generated by scripts/bluez-interfaces.py
#
# Do not edit this file manually.
#

import sdbus
"""

TEMPLATE_CLASS = """
class {name}Interface(
        sdbus.DbusInterfaceCommonAsync,
        interface_name="{interface}"):
"""

TEMPLATE_METHOD = """
    @sdbus.dbus_method_async(
        input_signature="{input_signature}",
        input_args_names={input_arguments},
        result_signature="{result_signature}",
        result_args_names={result_arguments},
        flags=sdbus.DbusUnprivilegedFlag)
    async def {name}(
        {params},
    ) -> {returns}:
        raise NotImplementedError
"""

TEMPLATE_SIGNAL = """
    @sdbus.dbus_signal_async(
        signal_signature="{signature}",
        signal_args_names={arguments})
    def {name}(self) -> {type}:
        raise NotImplementedError
"""

TEMPLATE_PROPERTY = """
    @sdbus.dbus_property_async(
        property_signature="{signature}",
        flags=sdbus.DbusPropertyEmitsChangeFlag)
    def {name}(self) -> {type}:
        raise NotImplementedError
"""


def save_python(name: str, interface: Interface):
    """Generate a Python file for the given interface."""

    def returns2type(returns):
        """Return the typing for the given returns."""
        if len(returns) == 1:
            return type2python(returns[0])
        return f"tuple[{', '.join(map(type2python, returns))}]"

    file = args.output_dir / f"{name}.py"
    if args.verbose:
        print(f"Generating {file}")
    with open(file, "w") as f:
        f.write(TEMPLATE_HEADER.lstrip())

        f.write("\n")
        f.write(TEMPLATE_CLASS.format(
            name=name,
            interface=interface.name))

        for method in interface.methods:
            params = ["self"]
            arguments = []
            for n, t in method.parameters:
                if s := type2signature(t):
                    params.append(f"{n}: {type2python(t)}")
                    arguments.append((n, s))
            results = []
            for t in method.returns:
                if s := type2signature(t):
                    results.append(s)
            f.write(TEMPLATE_METHOD.format(
                name=method.name,
                params=",\n        ".join(params),
                returns=returns2type(method.returns),
                input_signature="".join([x[1] for x in arguments]),
                input_arguments=list2python([x[0] for x in arguments]),
                result_signature="".join(results),
                result_arguments=list2python([f"r{i}" for i in range(len(results))]),
            ))

        for signal in interface.signals:
            f.write(TEMPLATE_SIGNAL.format(
                name=signal.name,
                type=returns2type([x[1] for x in signal.parameters]),
                signature="".join([type2signature(x[1]) for x in signal.parameters]),
                arguments=list2python([x[0] for x in signal.parameters]),
            ))

        for property in interface.properties:
            f.write(TEMPLATE_PROPERTY.format(
                name=property.name,
                type=type2python(property.type),
                signature=type2signature(property.type),
            ))


def save_xml(name: str, interface: Interface):
    """Generate an XML file for the given interface."""

    root = ET.Element("node")
    root.set("xmlns:doc", "http://www.freedesktop.org/dbus/1.0/doc.dtd")

    iface = ET.SubElement(root, "interface", name=interface.name)
    annotate(iface, interface.annotations)

    for method in interface.methods:
        elem = ET.SubElement(iface, "method", name=method.name)
        for i, t in enumerate(method.returns):
            if s := type2signature(t):
                ET.SubElement(elem, "arg", direction="out", name=f"r{i}", type=s)
        for n, t in method.parameters:
            if s := type2signature(t):
                ET.SubElement(elem, "arg", direction="in", name=n, type=s)
        annotate(elem, method.annotations)
        comment(iface, method.description)

    for signal in interface.signals:
        elem = ET.SubElement(iface, "signal", name=signal.name)
        for n, t in signal.parameters:
            ET.SubElement(elem, "arg", name=n, type=type2signature(t))
        annotate(elem, signal.annotations)
        comment(iface, signal.description)

    for prop in interface.properties:
        elem = ET.SubElement(iface, "property", name=prop.name,
                             type=type2signature(prop.type))
        annotate(elem, prop.annotations)
        comment(iface, prop.description)

    ET.indent(root, space="\t", level=0)
    file = args.output_dir / f"{name}.xml"
    if args.verbose:
        print(f"Generating {file}")
    ET.ElementTree(root).write(str(file))


def save(name: str, interface: Interface):
    if args.save_xml:
        save_xml(name, interface)
    save_python(name, interface)


for iface in interfaces:
    # Do not include namespaces and version in the interface name.
    name = iface.name.removeprefix("org.bluez.").rstrip("1")
    # Remove dot and capitalize the first letter for OBEX interfaces.
    name = name[0].upper() + name[1:].replace(".", "")

    # Split interface if some properties are annotated with adapter-only and
    # device-only. Example of such interface is org.bluez.AdminPolicyStatus
    # which is documented only once but in fact contains two different
    # functional interfaces.
    props_adapter = [x for x in iface.properties if "device-only" not in x.annotations]
    props_device = [x for x in iface.properties if "adapter-only" not in x.annotations]
    if props_adapter == props_device:
        save(name, iface)
    else:
        iface.properties = props_adapter
        save(f"Adapter{name}", iface)
        iface.properties = props_device
        save(f"Device{name}", iface)
