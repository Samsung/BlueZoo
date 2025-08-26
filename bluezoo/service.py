# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import asyncio
import logging
from argparse import ArgumentParser

from sdbus import DbusObjectManagerInterfaceAsync
from sdbus_async.dbus_daemon import FreedesktopDbus

from . import events
from .adapter import Adapter
from .bluezoo import BlueZooController
from .controller import Controller
from .device import Device
from .log import logger
from .utils import BluetoothAddress, BluetoothUUID, setup_default_bus


class BluezMockService:

    def __init__(self, adapter_auto_enable: bool, scan_interval: int):

        # Proxy for the D-Bus daemon interface used
        # for listening to ownership changes.
        self.dbus = FreedesktopDbus()
        self.dbus_task = asyncio.create_task(self._service_lost_task())

        # Register dedicated BlueZoo controller interface.
        self.bluezoo = BlueZooController(self)
        self.bluezoo.export_to_dbus("/org/bluezoo")

        self.manager = DbusObjectManagerInterfaceAsync()
        self.manager.export_to_dbus("/")

        self.controller = Controller(self)
        self.manager.export_with_manager(self.controller.get_object_path(), self.controller)

        self.adapters: dict[int, Adapter] = {}
        self.adapter_auto_enable = adapter_auto_enable
        self.scan_interval = scan_interval

    async def _service_lost_task(self):
        async for _, old, new in self.dbus.name_owner_changed.catch():
            if old and not new:
                logger.debug(f"D-Bus service {old} lost")
                events.emit(f"service:lost:{old}")

    async def add_adapter(self, id: int, address: str):
        adapter = Adapter(self.controller, id, address)
        logger.info(f"Adding {adapter}")
        self.manager.export_with_manager(adapter.get_object_path(), adapter)
        self.adapters[id] = adapter
        if self.adapter_auto_enable:
            await adapter.Powered.set_async(True)
        return adapter

    async def del_adapter(self, id: int):
        adapter = self.adapters.pop(id)
        logger.info(f"Removing {adapter}")
        for device in adapter.devices.values():
            await adapter.del_device(device)
        self.manager.remove_managed_object(adapter)

    def create_discovering_task(self, id: int):
        """Create a task that scans for devices on the adapter.

        The scan is performed every 10 seconds. The task checks for any other
        adapter which is powered and discoverable, and reports that adapter as
        a new device. The task runs indefinitely until it is cancelled.
        """
        is_scan_br_edr = self.adapters[id].scan_filter_transport in ("auto", "bredr")
        is_scan_le = self.adapters[id].scan_filter_transport in ("auto", "le")

        async def task():
            while True:
                logger.info(f"Scanning for devices on {self.adapters[id]}")
                for adapter in self.adapters.values():
                    if adapter.id == id:
                        # Do not report our own adapter.
                        continue
                    if not adapter.powered:
                        continue

                    # The adapter can be discoverable either if BR/EDR advertising
                    # is explicitly enabled or when the scan filter enables it.
                    is_adapter_discoverable = (
                        adapter.discoverable
                        or (adapter.discovering and
                            adapter.scan_filter_discoverable))
                    device = None

                    # Check if adapter has enabled LE advertising.
                    if is_scan_le and len(adapter.advertisements):
                        adv = next(iter(adapter.advertisements.values()))
                        # The LE advertisement discoverable property is not mandatory,
                        # but if present, it overrides the adapter's property.
                        if not adv.Discoverable.get(is_adapter_discoverable):
                            continue
                        device = Device(adapter, is_le=True)
                        device.name_ = adv.LocalName.get(adapter.name)
                        device.appearance = adv.Appearance.get(0)
                        device.uuids = [BluetoothUUID(x) for x in adv.ServiceUUIDs.get([])]
                        device.manufacturer_data = adv.ManufacturerData.get({})
                        device.service_data = {BluetoothUUID(k): v
                                               for k, v in adv.ServiceData.get({}).items()}
                        device.tx_power = adv.TxPower.get()
                        # Report discoverable LE device on our adapter.
                        await self.adapters[id].add_device(device)

                    # Check if adapter has enabled BR/EDR advertising.
                    if is_scan_br_edr and is_adapter_discoverable:
                        device = Device(adapter, is_br_edr=True)
                        # Report discoverable BR/EDR device on our adapter.
                        await self.adapters[id].add_device(device)

                # Wait for the next scan.
                await asyncio.sleep(self.scan_interval)

        return asyncio.create_task(task())


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
