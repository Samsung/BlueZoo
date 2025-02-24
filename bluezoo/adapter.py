# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import asyncio
import logging
import random

from .device import Device
from .interfaces import AdapterInterface, LEAdvertisingManagerInterface

# List of predefined device names.
TEST_NAMES = (
    "Alligator's Android",
    "Bobcat's Bluetooth",
    "Eagle's Earbuds",
    "Lion's Laptop",
    "MacBook Pro",
    "ThinkPad",
)


class Adapter(AdapterInterface, LEAdvertisingManagerInterface):

    # Number of supported advertisement instances per adapter.
    SUPPORTED_ADVERTISEMENT_INSTANCES = 15

    def __init__(self, service, id: int, address: str):
        self.service = service
        super().__init__()

        self.id = id
        self.address = address
        self.name_ = random.choice(TEST_NAMES)
        self.class_ = 0
        self.powered = False
        self.discoverable = False
        self.discoverable_timeout = 180
        self.discoverable_task = None
        self.pairable = False
        self.pairable_timeout = 0
        self.pairable_task = None
        self.discovering = False
        self.discovering_task = None
        self.uuids = []

        self.advertisements = {}
        self.devices = {}

    def get_object_path(self):
        return f"/org/bluez/hci{self.id}"

    @property
    def name(self):
        return getattr(self, "name__", self.name_)

    @name.setter
    def name_setter(self, value):
        self.name__ = value

    @property
    def advertisement_slots_active(self):
        return len(self.advertisements)

    @property
    def advertisement_slots_available(self):
        return self.SUPPORTED_ADVERTISEMENT_INSTANCES - len(self.advertisements)

    async def start_discovering(self):
        logging.info(f"Starting discovery on adapter {self.id}")
        self.discovering_task = self.service.create_discovering_task(self.id)
        await self.Discovering.set_async(True)

    async def stop_discovering(self):
        logging.info(f"Stopping discovery on adapter {self.id}")
        if self.discovering_task is not None:
            self.discovering_task.cancel()
        await self.Discovering.set_async(False)

    async def register_advertisement(self, advertisement):
        self.advertisements[advertisement.destination] = advertisement
        await self.ActiveInstances.set_async(self.advertisement_slots_active)
        await self.SupportedInstances.set_async(self.advertisement_slots_available)

    async def unregister_advertisement(self, advertisement):
        self.advertisements.pop(advertisement.destination)
        await self.ActiveInstances.set_async(self.advertisement_slots_active)
        await self.SupportedInstances.set_async(self.advertisement_slots_available)

    def add_device(self, device: Device):
        device.peer = self  # Set the device's peer controller.
        path = device.get_object_path()
        if path in self.devices:
            return
        logging.info(f"Adding device {device.address} to adapter {self.id}")
        self.service.manager.export_with_manager(path, device.iface)
        self.devices[path] = device

    def remove_device(self, device: Device):
        logging.info(f"Removing device {device.address} from adapter {self.id}")
        self.devices.pop(device.get_object_path())
        self.service.manager.remove_managed_object(device.iface)

    def set_discoverable(self, enabled: bool):
        self.discoverable = enabled
        if self.discoverable_task is not None:
            self.discoverable_task.cancel()
        if enabled:
            async def task():
                """Set the adapter as non-discoverable after the timeout."""
                await asyncio.sleep(self.discoverable_timeout)
                await self.Discoverable.set_async(False)
            # If timeout is non-zero, set up cancellation task.
            if timeout := self.discoverable_timeout:
                logging.info(f"Setting adapter {self.id} as discoverable for {timeout} seconds")
                self.discoverable_task = asyncio.create_task(task())

    def set_pairable(self, enabled: bool):
        self.pairable = enabled
        if self.pairable_task is not None:
            self.pairable_task.cancel()
        if enabled:
            async def task():
                """Set the adapter as non-pairable after the timeout."""
                await asyncio.sleep(self.pairable_timeout)
                await self.Pairable.set_async(False)
            # If timeout is non-zero, set up cancellation task.
            if timeout := self.pairable_timeout:
                logging.info(f"Setting adapter {self.id} as pairable for {timeout} seconds")
                self.pairable_task = asyncio.create_task(task())
