# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import asyncio
import logging
from typing import Any, Optional

from .device import Device
from .interfaces import AdapterInterface, GattManagerInterface, LEAdvertisingManagerInterface
from .interfaces.GattManager import GattApplication, GattService
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


class Adapter(AdapterInterface, GattManagerInterface, LEAdvertisingManagerInterface):

    # Number of supported advertisement instances per adapter.
    SUPPORTED_ADVERTISEMENT_INSTANCES = 15

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

        self.advertisements = {}
        self.gatt_apps = {}
        self.gatt_handles = set()
        self.gatt_handle_counter = 0
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

    async def start_discovering(self, client):
        logging.info(f"Starting discovery on {self}")
        self.service.on_client_lost(client, self.stop_discovering)
        self.discovering_task = self.service.create_discovering_task(self.id)
        await self.Discovering.set_async(True)

    async def stop_discovering(self):
        logging.info(f"Stopping discovery on {self}")
        self.discovering_task.cancel()
        await self.Discovering.set_async(False)

    async def add_le_advertisement(self, adv):
        logging.info(f"Adding LE advertisement {adv.get_object_path()}")

        self.advertisements[adv.get_destination()] = adv

        async def on_client_lost():
            await self.del_le_advertisement(adv)
        self.service.on_client_lost(adv.get_client(), on_client_lost)
        adv.on_client_lost = on_client_lost

        await self.ActiveInstances.set_async(self.advertisement_slots_active)
        await self.SupportedInstances.set_async(self.advertisement_slots_available)

    async def del_le_advertisement(self, adv):
        logging.info(f"Removing LE advertisement {adv.get_object_path()}")

        self.service.on_client_lost_remove(adv.get_client(), adv.on_client_lost)
        self.advertisements.pop(adv.get_destination())

        await self.ActiveInstances.set_async(self.advertisement_slots_active)
        await self.SupportedInstances.set_async(self.advertisement_slots_available)

    async def add_gatt_application(self, app: GattApplication) -> None:
        logging.info(f"Adding GATT application {app.get_object_path()}")

        self.gatt_apps[app.get_destination()] = app

        for obj in app.objects.values():
            # Assign handle values to objects that don't have one.
            if obj.Handle.get() == 0:
                self.gatt_handle_counter += 1
                # Let the server know the new handle value.
                await obj.Handle.set_async(self.gatt_handle_counter)
            elif obj.Handle.get() is None:
                self.gatt_handle_counter += 1
                # If server does not have the Handle property, update local cache only.
                obj.Handle.cache(self.gatt_handle_counter)
            elif obj.Handle.get() in self.gatt_handles:
                raise ValueError(f"Handle {obj.Handle.get()} already exists")
            self.gatt_handles.add(obj.Handle.get())

        await self.update_uuids()

        async def on_client_lost():
            await self.del_gatt_application(app)
        self.service.on_client_lost(app.get_client(), on_client_lost)
        app.on_client_lost = on_client_lost

        async def wait_for_object_removed():
            await app.object_removed.wait()
            path = app.get_object_path()
            logging.debug(f"Object removed, removing GATT application {path}")
            await self.del_gatt_application(app)

        app.client_lost_task = asyncio.create_task(asyncio.wait(
            [wait_for_object_removed()],
            return_when=asyncio.FIRST_COMPLETED))

    async def del_gatt_application(self, app: GattApplication) -> None:
        logging.info(f"Removing GATT application {app.get_object_path()}")
        app.client_lost_task.cancel()
        self.service.on_client_lost_remove(app.get_client(), app.on_client_lost)
        self.gatt_apps.pop(app.get_destination())
        await self.update_uuids()

    def get_gatt_application(self, client, path) -> Optional[GattApplication]:
        self.gatt_apps.get((client, path))

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
