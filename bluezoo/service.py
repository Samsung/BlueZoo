# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import asyncio
import logging

from sdbus import DbusObjectManagerInterfaceAsync

from .adapter import Adapter
from .controller import Controller
from .device import Device


class BluezMockService:

    def __init__(self):

        self.manager = DbusObjectManagerInterfaceAsync()
        self.manager.export_to_dbus("/")

        self.controller = Controller(self)
        self.manager.export_with_manager(self.controller.get_object_path(), self.controller)

        self.adapters: dict[int, Adapter] = {}

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
        async def task():
            while True:
                logging.info(f"Scanning for devices on adapter {id}")
                for adapter in self.adapters.values():
                    if adapter.id == id:
                        # Do not report our own adapter.
                        continue
                    if not adapter.powered:
                        continue
                    device = None
                    # Check if adapter has enabled LE advertising.
                    if adapter.advertisement_slots_active > 0:
                        adv = next(iter(adapter.advertisements.values()))
                        adv_props = await adv.properties_get_all_dict()
                        # The LE advertisement discoverable property is not mandatory,
                        # but if present, it overrides the adapter's property.
                        if not adv_props.get("Discoverable", adapter.discoverable):
                            continue
                        device = Device(adapter)
                        device.name_ = adv_props.get("LocalName", adapter.name)
                        device.appearance = adv_props.get("Appearance", 0)
                        device.uuids = adv_props.get("ServiceUUIDs", [])
                        device.service_data = adv_props.get("ServiceData", {})
                    # Check if adapter has enabled BR/EDR advertising.
                    elif adapter.discoverable:
                        device = Device(adapter)
                    if device is not None:
                        # Report discoverable device on our adapter.
                        self.adapters[id].add_device(device)
                await asyncio.sleep(10)
        return asyncio.create_task(task())
