# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import asyncio
import logging
import weakref
from typing import Any

import sdbus
from sdbus.utils import parse_get_managed_objects

from .GattService import GattServiceInterface
from .GattCharacteristic import GattCharacteristicInterface
from .GattDescriptor import GattDescriptorInterface
from ..helpers import dbus_method_async, DBusClientMixin


class GattService(DBusClientMixin, GattServiceInterface):
    """D-Bus client for GATT service."""

    def __init__(self, service, path):
        super().__init__(service, path)


class GattCharacteristic(DBusClientMixin, GattCharacteristicInterface):
    """D-Bus client for GATT characteristic."""

    def __init__(self, service, path):
        super().__init__(service, path)


class GattDescriptor(DBusClientMixin, GattDescriptorInterface):
    """D-Bus client for GATT descriptor."""

    def __init__(self, service, path):
        super().__init__(service, path)


class GattApplication(DBusClientMixin, sdbus.DbusObjectManagerInterfaceAsync):
    """D-Bus client for registered GATT application."""

    def __init__(self, service, path, options):
        super().__init__(service, path)
        self.options = options

        self.objects = {}
        self.object_removed = asyncio.Event()

    async def _obj_mgr_watch(self):
        async for path, ifaces in self.interfaces_removed.catch():
            self.objects.pop(path, None)
            self.object_removed.set()

    def _obj_mgr_watch_task_cancel(self):
        self._obj_mgr_watch_task.cancel()

    async def object_manager_setup_sync_task(self, interfaces):
        """Synchronize cached objects with the D-Bus service."""

        client, _ = self.get_client()
        objects = parse_get_managed_objects(
            interfaces,
            await self.get_managed_objects(),
            on_unknown_interface="ignore",
            on_unknown_member="ignore")

        for path, (iface, values) in objects.items():
            if iface not in interfaces:
                continue
            obj = iface(client, path)
            await obj.properties_setup_sync_task()
            self.objects[path] = obj

        self._obj_mgr_watch_task = asyncio.create_task(self._obj_mgr_watch())
        weakref.finalize(self, self._obj_mgr_watch_task_cancel)


class GattManagerInterface(sdbus.DbusInterfaceCommonAsync,
                           interface_name="org.bluez.GattManager1"):

    async def add_gatt_application(self, app: GattApplication) -> None:
        raise NotImplementedError

    async def del_gatt_application(self, app: GattApplication) -> None:
        raise NotImplementedError

    def get_gatt_application(self, client, path) -> GattApplication:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="oa{sv}",
        input_args_names=("application", "options"))
    async def RegisterApplication(self, application: str,
                                  options: dict[str, tuple[str, Any]]) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to register GATT application {application}")
        app = GattApplication(sender, application, options)
        await app.object_manager_setup_sync_task(
            (GattService, GattCharacteristic, GattDescriptor))
        await self.add_gatt_application(app)

    @dbus_method_async(
        input_signature="o",
        input_args_names=("application",))
    async def UnregisterApplication(self, application: str) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to unregister GATT application {application}")
        await self.del_gatt_application(self.get_gatt_application(sender, application))
