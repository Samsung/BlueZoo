# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import asyncio
import logging
from argparse import ArgumentParser

from .helpers import setup_default_bus, validate_bt_address
from .service import BluezMockService


async def main_async():

    parser = ArgumentParser(description="BlueZ D-Bus Mock Service")
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="enable verbose output")
    parser.add_argument(
        "--bus-session", action="store_true",
        help="use the session bus; default is the system bus")
    parser.add_argument(
        "-a", "--adapter", metavar="ADDRESS", dest="adapters",
        action="append", type=validate_bt_address,
        help="adapter to use")

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    bus = setup_default_bus("session" if args.bus_session else "system")
    await bus.request_name_async("org.bluez", 0)
    service = BluezMockService(bus)

    for i, address in enumerate(args.adapters):
        service.add_adapter(i, address)

    while True:
        # Run forever...
        await asyncio.sleep(1000)


def main():
    asyncio.run(main_async())
