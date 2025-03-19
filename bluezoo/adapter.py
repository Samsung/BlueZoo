# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import asyncio
import logging
from typing import Any

from .adv import LEAdvertisingManager
from .device import Device
from .gatt import GattManager
from .interfaces.Adapter import AdapterInterface
from .utils import BluetoothClass, BluetoothUUID, NoneTask

# List of predefined device names.
TEST_NAMES = (
    "Alligator's Android",
    "Bobcat's Bluetooth",
    "Eagle's Earbuds",
    "Lion's Laptop",
    "MacBook Pro",
    "ThinkPad",
)


class Adapter(AdapterInterface, LEAdvertisingManager, GattManager):

    def __init__(self, controller, id: int, address: str):
        self.controller = controller
        self.service = controller.service
        super().__init__()

        self.id = id
        self.address = address
        self.name_ = TEST_NAMES[id % len(TEST_NAMES)]
        self.class_ = BluetoothClass(BluetoothClass.Major.Computer)
        self.powered = False
        self.discoverable = False
        self.discoverable_timeout = 180
        self.discoverable_task = NoneTask()
        self.pairable = False
        self.pairable_timeout = 0
        self.pairable_task = NoneTask()
        self.discovering = False
        self.discovering_task = NoneTask()
        self.uuids = []

        self.scan_filter_uuids = []
        self.scan_filter_transport = "auto"
        self.scan_filter_duplicate = False
        self.scan_filter_discoverable = False
        self.scan_filter_pattern = None

        self.devices = {}

    def __str__(self):
        return f"adapter[{self.id}][{self.address}]"

    def get_object_path(self):
        return f"/org/bluez/hci{self.id}"

    @property
    def name(self):
        return getattr(self, "name__", self.name_)

    @name.setter
    def name_setter(self, value):
        self.name__ = value

    async def update_uuids(self):
        uuids = set()
        uuids.update(self.get_gatt_registered_primary_services())
        await self.UUIDs.set_async(list(uuids))

    async def start_discovering(self, client):
        logging.info(f"Starting discovery on {self}")
        self.service.on_client_lost(client, self.stop_discovering)
        self.discovering_task = self.service.create_discovering_task(self.id)
        await self.Discovering.set_async(True)

    async def stop_discovering(self):
        logging.info(f"Stopping discovery on {self}")
        self.discovering_task.cancel()
        await self.Discovering.set_async(False)

    async def add_device(self, device: Device):
        device.setup_adapter(self)
        path = device.get_object_path()
        if path in self.devices:
            logging.debug(f"Updating {device} in {self}")
            await self.devices[path].properties_sync(device)
            return
        logging.info(f"Adding {device} to {self}")
        self.service.manager.export_with_manager(path, device)
        self.devices[path] = device

    async def del_device(self, device: Device):
        logging.info(f"Removing {device} from {self}")
        self.devices.pop(device.get_object_path())
        self.service.manager.remove_managed_object(device)

    def set_discovery_filter(self, properties: dict[str, tuple[str, Any]]) -> None:
        if value := properties.get("UUIDs"):
            self.scan_filter_uuids = [BluetoothUUID(x) for x in value[1]]
        if value := properties.get("Transport"):
            self.scan_filter_transport = value[1]
        if value := properties.get("DuplicateData"):
            self.scan_filter_duplicate = value[1]
        if value := properties.get("Discoverable"):
            self.scan_filter_discoverable = value[1]
        if value := properties.get("Pattern"):
            self.scan_filter_pattern = value[1]

    def set_discoverable(self, enabled: bool):
        self.discoverable = enabled
        self.discoverable_task.cancel()
        if enabled:
            async def task():
                """Set the adapter as non-discoverable after the timeout."""
                await asyncio.sleep(self.discoverable_timeout)
                await self.Discoverable.set_async(False)
            # If timeout is non-zero, set up cancellation task.
            if timeout := self.discoverable_timeout:
                logging.info(f"Setting {self} as discoverable for {timeout} seconds")
                self.discoverable_task = asyncio.create_task(task())

    def set_pairable(self, enabled: bool):
        self.pairable = enabled
        self.pairable_task.cancel()
        if enabled:
            async def task():
                """Set the adapter as non-pairable after the timeout."""
                await asyncio.sleep(self.pairable_timeout)
                await self.Pairable.set_async(False)
            # If timeout is non-zero, set up cancellation task.
            if timeout := self.pairable_timeout:
                logging.info(f"Setting {self} as pairable for {timeout} seconds")
                self.pairable_task = asyncio.create_task(task())
