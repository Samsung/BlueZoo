# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import asyncio
import logging
import random

from .device import Device
from .helpers import NoneTask
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

    def __init__(self, controller, id: int, address: str):
        self.controller = controller
        super().__init__()

        self.id = id
        self.address = address
        self.name_ = random.choice(TEST_NAMES)
        self.class_ = 0
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
        self.discovering_task = self.controller.service.create_discovering_task(self.id)
        await self.Discovering.set_async(True)

    async def stop_discovering(self):
        logging.info(f"Stopping discovery on adapter {self.id}")
        self.discovering_task.cancel()
        await self.Discovering.set_async(False)

    async def add_le_advertisement(self, advertisement):

        self.advertisements[advertisement.get_client()] = advertisement

        async def wait_for_client_lost():
            client, path = advertisement.get_client()
            await self.controller.service.wait_for_client_lost(client)
            logging.debug(f"Client {client} lost, removing LE advertisement {path}")
            await self.del_le_advertisement(advertisement)
        advertisement.client_lost_task = asyncio.create_task(wait_for_client_lost())

        await self.ActiveInstances.set_async(self.advertisement_slots_active)
        await self.SupportedInstances.set_async(self.advertisement_slots_available)

    async def del_le_advertisement(self, advertisement):

        advertisement.client_lost_task.cancel()
        self.advertisements.pop(advertisement.get_client())

        await self.ActiveInstances.set_async(self.advertisement_slots_active)
        await self.SupportedInstances.set_async(self.advertisement_slots_available)

    def add_device(self, device: Device):
        device.peer = self  # Set the device's peer adapter.
        path = device.get_object_path()
        if path in self.devices:
            return
        logging.info(f"Adding device {device.address} to adapter {self.id}")
        self.controller.service.manager.export_with_manager(path, device)
        self.devices[path] = device

    def remove_device(self, device: Device):
        logging.info(f"Removing device {device.address} from adapter {self.id}")
        self.devices.pop(device.get_object_path())
        self.controller.service.manager.remove_managed_object(device)

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
                logging.info(f"Setting adapter {self.id} as discoverable for {timeout} seconds")
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
                logging.info(f"Setting adapter {self.id} as pairable for {timeout} seconds")
                self.pairable_task = asyncio.create_task(task())
