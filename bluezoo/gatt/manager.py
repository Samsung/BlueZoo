# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import asyncio
import logging
from typing import Any, Iterable

import sdbus

from ..interfaces.GattManager import GattManagerInterface
from ..utils import BluetoothUUID, dbus_method_async_except_logging
from .application import GattApplicationClient
from .characteristic import GattCharacteristicClient
from .descriptor import GattDescriptorClient
from .service import GattServiceClient


class GattManager(GattManagerInterface):
    """GATT manager."""

    def __init__(self):
        super().__init__()

        self.gatt_apps = {}
        self.gatt_handles = set()
        self.gatt_handle_counter = 0

    async def __del_gatt_application(self, app: GattApplicationClient) -> None:
        logging.info(f"Removing GATT application {app.get_object_path()}")
        app.obj_removed_task.cancel()
        self.service.on_client_lost_remove(app.get_client(), app.on_client_lost)
        self.gatt_apps.pop((app.get_client(), app.get_object_path()))
        await self.update_uuids()

    def get_gatt_registered_primary_services(self) -> Iterable[BluetoothUUID]:
        """Get UUIDs of all registered primary services."""
        for app in self.gatt_apps.values():
            for obj in app.objects.values():
                if isinstance(obj, GattServiceClient) and obj.Primary.get():
                    yield BluetoothUUID(obj.UUID.get())

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def RegisterApplication(self, application: str,
                                  options: dict[str, tuple[str, Any]]) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to register GATT application {application}")

        app = GattApplicationClient(sender, application, options)
        await app.object_manager_setup_sync_task(
            (GattServiceClient, GattCharacteristicClient, GattDescriptorClient))

        logging.info(f"Adding GATT application {app.get_object_path()}")
        self.gatt_apps[sender, application] = app

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
            await self.__del_gatt_application(app)
        self.service.on_client_lost(app.get_client(), on_client_lost)
        app.on_client_lost = on_client_lost

        async def wait_for_object_removed():
            await app.object_removed.wait()
            path = app.get_object_path()
            logging.debug(f"Object removed, removing GATT application {path}")
            await self.__del_gatt_application(app)
        app.obj_removed_task = asyncio.create_task(wait_for_object_removed())

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def UnregisterApplication(self, application: str) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to unregister GATT application {application}")
        await self.__del_gatt_application(self.gatt_apps[sender, application])
