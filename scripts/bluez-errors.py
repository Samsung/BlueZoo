#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import re
from argparse import ArgumentParser
from pathlib import Path

parser = ArgumentParser(description="Generate mappings for BlueZ D-Bus errors")
parser.add_argument("--output", type=Path, default=Path("exceptions.py"),
                    help="output file; defaults to %(default)s")
parser.add_argument("inputs", metavar="INPUT", type=Path, nargs="+",
                    help="input file(s)")

args = parser.parse_args()

# Regular expression to match BlueZ D-Bus errors.
re_error = re.compile(r"org\.bluez\.Error\.(\w+)")

errors = set()
# Read all files in the given directory and search for BlueZ D-Bus errors.
for file in args.inputs:
    with open(file) as f:
        for line in f:
            if match := re_error.search(line):
                errors.add(match.group(1))

with open(args.output, "w") as f:
    f.write("# SPDX-FileCopyrightText: 2025 BlueZoo developers\n")
    f.write("# SPDX-License-Identifier: GPL-2.0-only\n\n")
    f.write("import sdbus\n")
    for error in sorted(errors):
        f.write("\n\n")
        f.write(f"class DBusBluez{error}Error(sdbus.DbusFailedError):\n")
        f.write(f"    dbus_error_name = \"org.bluez.Error.{error}\"\n")
