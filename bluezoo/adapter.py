# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import asyncio
import logging
import random
from typing import Any, Optional

from .device import Device
from .interfaces import AdapterInterface, GattManagerInterface, LEAdvertisingManagerInterface
from .interfaces.GattManager import GattApplication, GattService
from .utils import BluetoothUUID, NoneTask

# List of predefined device names.
TEST_NAMES = (
    "Alligator's Android",
    "Bobcat's Bluetooth",
    "Eagle's Earbuds",
    "Lion's Laptop",
    "MacBook Pro",
    "ThinkPad",
)


class Adapter(AdapterInterface, GattManagerInterface, LEAdvertisingManagerInterface):

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

        self.scan_filter_uuids = []
        self.scan_filter_transport = "auto"
        self.scan_filter_duplicate = False
        self.scan_filter_discoverable = False
        self.scan_filter_pattern = None

        self.advertisements = {}
        self.gatt_apps = {}
        self.gatt_handle_counter = 0
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

    async def update_uuids(self):
        uuids = set()

        # Gather all UUIDs from GATT applications.
        for app in self.gatt_apps.values():
            for obj in app.objects.values():
                if isinstance(obj, GattService) and obj.Primary.get():
                    uuids.add(BluetoothUUID(obj.UUID.get()))

        await self.UUIDs.set_async(list(uuids))

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

    async def add_gatt_application(self, app: GattApplication) -> None:
        logging.info("Adding GATT application")

        self.gatt_apps[app.get_client()] = app

        for obj in app.objects.values():
            if obj.Handle.get() == 0:
                self.gatt_handle_counter += 1
                # Assign handle values to objects that don't have one.
                await obj.Handle.set_async(self.gatt_handle_counter)

        await self.update_uuids()

        async def wait_for_client_lost():
            client, path = app.get_client()
            await self.controller.service.wait_for_client_lost(client)
            logging.debug(f"Client {client} lost, removing GATT application {path}")
            await self.del_gatt_application(app)

        async def wait_for_object_removed():
            await app.object_removed.wait()
            _, path = app.get_client()
            logging.debug(f"Object removed, removing GATT application {path}")
            await self.del_gatt_application(app)

        app.client_lost_task = asyncio.create_task(asyncio.wait(
            [wait_for_client_lost(), wait_for_object_removed()],
            return_when=asyncio.FIRST_COMPLETED))

    async def del_gatt_application(self, app: GattApplication) -> None:
        logging.info("Removing GATT application")
        app.client_lost_task.cancel()
        self.gatt_apps.pop(app.get_client())
        await self.update_uuids()

    def get_gatt_application(self, client, path) -> Optional[GattApplication]:
        self.gatt_apps.get((client, path))

    async def add_device(self, device: Device):
        device.peer = self  # Set the device's peer adapter.
        path = device.get_object_path()
        if path in self.devices:
            logging.debug(f"Updating device {device.address} in adapter {self.id}")
            await self.devices[path].properties_sync(device)
            return
        logging.info(f"Adding device {device.address} to adapter {self.id}")
        self.controller.service.manager.export_with_manager(path, device)
        self.devices[path] = device

    async def del_device(self, device: Device):
        logging.info(f"Removing device {device.address} from adapter {self.id}")
        self.devices.pop(device.get_object_path())
        self.controller.service.manager.remove_managed_object(device)

    def set_discovery_filter(self, properties: dict[str, tuple[str, Any]]) -> None:
        if value := properties.get("UUIDs"):
            self.scan_filter_uuids = [BluetoothUUID(x[1]) for x in value]
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
