# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import asyncio
import logging
from argparse import ArgumentParser

from .service import BluezMockService
from .utils import BluetoothAddress, setup_default_bus


async def startup(args):

    bus = setup_default_bus("session" if args.bus_session else "system")
    await bus.request_name_async("org.bluez", 0)
    service = BluezMockService(args.auto_enable, args.scan_interval)

    for i, address in enumerate(args.adapters or []):
        await service.add_adapter(i, address)


def main():

    parser = ArgumentParser(description="BlueZ D-Bus Mock Service")
    parser.add_argument(
        "-v", "--verbose", action="count", default=0,
        help="increase verbosity level (can be used multiple times)")
    parser.add_argument(
        "-q", "--quiet", action="count", default=0,
        help="decrease verbosity level (can be used multiple times)")
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
    verbosity = logging.INFO + 10 * (args.quiet - args.verbose)
    logging.basicConfig(level=max(logging.DEBUG, min(logging.CRITICAL, verbosity)))

    loop = asyncio.new_event_loop()
    loop.run_until_complete(startup(args))
    loop.run_forever()
