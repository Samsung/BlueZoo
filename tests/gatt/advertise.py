#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import asyncio
import signal
from argparse import ArgumentParser

import sdbus

from bluezoo.interfaces.LEAdvertisingManager import LEAdvertisingManagerInterface
from bluezoo.utils import setup_default_bus

parser = ArgumentParser()
parser.add_argument("--adapter", metavar="ADAPTER", default="hci0",
                    help="adapter to use; default: %(default)s")
parser.add_argument("--timeout", metavar="SECONDS", type=int, default=60,
                    help="advertising timeout; default: %(default)s")
parser.add_argument("--type", choices=["broadcast", "peripheral"], default="peripheral",
                    help="advertisement type; default: %(default)s")
parser.add_argument("--service", metavar="UUID", default="0xF000",
                    help="GATT service UUID; default: %(default)s")
parser.add_argument("--discoverable", action="store_true",
                    help="advertise as general discoverable")
parser.add_argument("--appearance", metavar="NUM", type=int,
                    help="advertisement appearance")
parser.add_argument("--name", metavar="NAME",
                    help="advertisement local name")

args = parser.parse_args()
loop = asyncio.new_event_loop()
setup_default_bus("system")


class AdvertisementInterface(
        sdbus.DbusInterfaceCommonAsync,
        interface_name="org.bluez.LEAdvertisement1"):

    @sdbus.dbus_method_async(
        flags=sdbus.DbusUnprivilegedFlag)
    async def Release(self):
        loop.stop()

    @sdbus.dbus_property_async(
        property_signature="s",
        flags=sdbus.DbusPropertyEmitsChangeFlag)
    def Type(self) -> str:
        return args.type

    @sdbus.dbus_property_async(
        property_signature="as",
        flags=sdbus.DbusPropertyEmitsChangeFlag)
    def ServiceUUIDs(self) -> list[str]:
        return [args.service]

    @sdbus.dbus_property_async(
        property_signature="b",
        flags=sdbus.DbusPropertyEmitsChangeFlag)
    def Discoverable(self) -> bool:
        return args.discoverable

    @sdbus.dbus_property_async(
        property_signature="as",
        flags=sdbus.DbusPropertyEmitsChangeFlag)
    def Includes(self) -> list[str]:
        return []

    if args.name:
        @sdbus.dbus_property_async(
            property_signature="s",
            flags=sdbus.DbusPropertyEmitsChangeFlag)
        def LocalName(self) -> str:
            return args.name

    if args.appearance is not None:
        @sdbus.dbus_property_async(
            property_signature="q",
            flags=sdbus.DbusPropertyEmitsChangeFlag)
        def Appearance(self) -> int:
            return args.appearance

    @sdbus.dbus_property_async(
        property_signature="q",
        flags=sdbus.DbusPropertyEmitsChangeFlag)
    def Timeout(self) -> int:
        return args.timeout


manager = sdbus.DbusObjectManagerInterfaceAsync()
manager.export_to_dbus("/")

adv = AdvertisementInterface()
manager.export_with_manager("/adv", adv)

adapter = f"/org/bluez/{args.adapter}"
adv_manager = LEAdvertisingManagerInterface.new_proxy("org.bluez", adapter)


async def startup():
    await adv_manager.RegisterAdvertisement("/adv", {})
    print(f"Advertising {args.service} on {args.adapter}")


loop.run_until_complete(startup())

loop.add_signal_handler(signal.SIGINT, lambda: loop.stop())
loop.add_signal_handler(signal.SIGTERM, lambda: loop.stop())
loop.run_forever()
