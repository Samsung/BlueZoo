# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import asyncio
import logging
from collections import defaultdict

from sdbus import DbusObjectManagerInterfaceAsync
from sdbus_async.dbus_daemon import FreedesktopDbus

from .adapter import Adapter
from .controller import Controller
from .device import Device
from .utils import BluetoothUUID


class BluezMockService:

    def __init__(self, scan_interval: int):

        # Proxy for the D-Bus daemon interface used
        # for listening to ownership changes.
        self.dbus = FreedesktopDbus()
        self.dbus_task = asyncio.create_task(self._client_lost_task())
        self.dbus_clients: dict[str, list[asyncio.Event]] = defaultdict(list)

        self.manager = DbusObjectManagerInterfaceAsync()
        self.manager.export_to_dbus("/")

        self.controller = Controller(self)
        self.manager.export_with_manager(self.controller.get_object_path(), self.controller)

        self.adapters: dict[int, Adapter] = {}
        self.scan_interval = scan_interval

    async def _client_lost_task(self):
        async for _, old, new in self.dbus.name_owner_changed.catch():
            if old and not new:  # Client lost.
                for client in self.dbus_clients.pop(old, []):
                    client.set()

    async def wait_for_client_lost(self, client: str):
        """Wait until the D-Bus client is lost."""
        event = asyncio.Event()
        self.dbus_clients[client].append(event)
        await event.wait()

    def add_adapter(self, id: int, address: str):
        logging.info(f"Adding adapter {id} with address {address}")
        adapter = Adapter(self.controller, id, address)
        self.manager.export_with_manager(adapter.get_object_path(), adapter)
        self.adapters[id] = adapter
        return adapter

    def del_adapter(self, id: int):
        logging.info(f"Removing adapter {id}")
        self.manager.remove_managed_object(self.adapters.pop(id))

    def create_discovering_task(self, id: int):
        """Create a task that scans for devices on the adapter.

        The scan is performed every 10 seconds. The task checks for any other
        adapter which is powered and discoverable, and reports that adapter as
        a new device. The task runs indefinitely until it is cancelled.
        """
        is_scan_br = self.adapters[id].scan_filter_transport in ("auto", "bredr")
        is_scan_le = self.adapters[id].scan_filter_transport in ("auto", "le")

        async def task():
            while True:
                logging.info(f"Scanning for devices on adapter {id}")
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
                    if is_scan_le and adapter.advertisement_slots_active > 0:
                        adv = next(iter(adapter.advertisements.values()))
                        # The LE advertisement discoverable property is not mandatory,
                        # but if present, it overrides the adapter's property.
                        if not adv.Discoverable.get(is_adapter_discoverable):
                            continue
                        device = Device(adapter)
                        device.name_ = adv.LocalName.get(adapter.name)
                        device.appearance = adv.Appearance.get(0)
                        device.uuids = [BluetoothUUID(x) for x in adv.ServiceUUIDs.get([])]
                        device.service_data = {BluetoothUUID(k): v
                                               for k, v in adv.ServiceData.get({}).items()}
                    # Check if adapter has enabled BR/EDR advertising.
                    elif is_scan_br and is_adapter_discoverable:
                        device = Device(adapter)
                    if device is not None:
                        # Report discoverable device on our adapter.
                        await self.adapters[id].add_device(device)
                # Wait for the next scan.
                await asyncio.sleep(self.scan_interval)
        return asyncio.create_task(task())
