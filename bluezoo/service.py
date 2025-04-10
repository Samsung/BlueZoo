# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import asyncio
import logging
from collections import defaultdict

from sdbus import DbusObjectManagerInterfaceAsync
from sdbus_async.dbus_daemon import FreedesktopDbus

from .adapter import Adapter
from .bluezoo import BlueZooController
from .controller import Controller
from .device import Device
from .utils import BluetoothUUID


class EventEmitter:
    """Event registration and emitting."""

    def __init__(self):
        self.listeners = defaultdict(list)

    def __contains__(self, event: str):
        return event in self.listeners

    def on(self, event: str, coroutine):
        self.listeners[event].append(coroutine)

    def remove(self, event: str, coroutine=None):
        """Remove the event listener or all listeners."""
        if coroutine is not None:
            self.listeners[event].remove(coroutine)
        else:
            self.listeners.pop(event, None)

    async def emit(self, event: str, *args, **kwargs):
        if event in self.listeners:
            for coroutine in self.listeners[event]:
                await coroutine(*args, **kwargs)


class BluezMockService:

    def __init__(self, adapter_auto_enable: bool, scan_interval: int):

        # Proxy for the D-Bus daemon interface used
        # for listening to ownership changes.
        self.dbus = FreedesktopDbus()
        self.dbus_task = asyncio.create_task(self._client_lost_task())

        # Event emitter engine.
        self.events = EventEmitter()

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

    async def _client_lost_task(self):
        async for _, old, new in self.dbus.name_owner_changed.catch():
            if old and not new:  # Client lost.
                event = f"client:lost:{old}"
                if event in self.events:
                    logging.debug(f"Client {old} lost")
                    await self.events.emit(f"client:lost:{old}")
                    self.events.remove(f"client:lost:{old}")

    def on_client_lost(self, client: str, coroutine):
        """Execute the coroutine on the client lost event."""
        self.events.on(f"client:lost:{client}", coroutine)

    def on_client_lost_remove(self, client: str, coroutine):
        self.events.remove(f"client:lost:{client}", coroutine)

    async def add_adapter(self, id: int, address: str):
        adapter = Adapter(self.controller, id, address)
        adapter.powered = self.adapter_auto_enable
        logging.info(f"Adding {adapter}")
        self.manager.export_with_manager(adapter.get_object_path(), adapter)
        self.adapters[id] = adapter
        return adapter

    async def del_adapter(self, id: int):
        adapter = self.adapters.pop(id)
        logging.info(f"Removing {adapter}")
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
                logging.info(f"Scanning for devices on {self.adapters[id]}")
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
