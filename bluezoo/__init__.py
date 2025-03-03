# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import asyncio
import logging
from argparse import ArgumentParser

from .service import BluezMockService
from .utils import BluetoothAddress, setup_default_bus


async def main_async():

    parser = ArgumentParser(description="BlueZ D-Bus Mock Service")
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="enable verbose output")
    parser.add_argument(
        "--bus-session", action="store_true",
        help="use the session bus; default is the system bus")
    parser.add_argument(
        "--auto-enable", action="store_true",
        help="auto-enable adapters")
    parser.add_argument(
        "--scan-interval", type=int, default=10,
        help="interval between scans; default is %(default)s seconds")
    parser.add_argument(
        "-a", "--adapter", metavar="ADDRESS", dest="adapters",
        action="append", type=BluetoothAddress,
        help="adapter to use")

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    bus = setup_default_bus("session" if args.bus_session else "system")
    await bus.request_name_async("org.bluez", 0)
    service = BluezMockService(args.scan_interval)

    for i, address in enumerate(args.adapters):
        adapter = service.add_adapter(i, address)
        adapter.powered = args.auto_enable

    while True:
        # Run forever...
        await asyncio.sleep(1000)


def main():
    asyncio.run(main_async())
