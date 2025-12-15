# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

from collections.abc import Iterable
from typing import Any

import sdbus

from ..exceptions import DBusBluezDoesNotExistError
from ..interfaces.GattManager import GattManagerInterface
from ..log import logger
from ..utils import BluetoothUUID, dbus_method_async_except_logging
from .application import GattApplicationClient
from .characteristic import GattCharacteristicClient
from .descriptor import GattDescriptorClient
from .service import GattServiceClient


class GattManager(GattManagerInterface):
    """GATT manager."""

    def __init__(self, adapter):
        super().__init__()
        # Keep track of registered GATT applications.
        self.apps: dict[tuple[str, str], GattApplicationClient] = {}

        self._adapter = adapter
        self._handles = set()
        self._handle_counter = 0

    async def cleanup(self):
        for app in self.apps.values():
            await app.cleanup()

    async def __del_gatt_application(self, app: GattApplicationClient) -> None:
        logger.info(f"Removing GATT application {app.get_object_path()}")
        self.apps.pop((app.get_client(), app.get_object_path()), None)
        await app.cleanup()
        await self._adapter.update_uuids()

    def get_primary_services(self) -> Iterable[BluetoothUUID]:
        """Get UUIDs of all registered primary services."""
        for app in self.apps.values():
            for obj in app.objects.values():
                if isinstance(obj, GattServiceClient) and obj.Primary.get():
                    yield BluetoothUUID(obj.UUID.get())

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def RegisterApplication(self, application: str,
                                  options: dict[str, tuple[str, Any]]) -> None:
        sender = sdbus.get_current_message().sender
        logger.debug(f"Client {sender} requested to register GATT application {application}")
        assert sender is not None, "D-Bus message sender is None"

        async def on_sender_lost():
            await self.__del_gatt_application(app)

        app = GattApplicationClient(sender, application, options, on_sender_lost)
        await app.object_manager_setup_sync_task(
            (GattServiceClient, GattCharacteristicClient, GattDescriptorClient))

        logger.info(f"Adding GATT application {app.get_object_path()}")
        self.apps[sender, application] = app

        for obj in app.objects.values():
            # Assign handle values to objects that don't have one.
            if obj.Handle.get() == 0:
                self._handle_counter += 1
                # Let the server know the new handle value.
                await obj.Handle.set_async(self._handle_counter)
            elif obj.Handle.get() is None:
                self._handle_counter += 1
                # If server does not have the Handle property, update local cache only.
                obj.Handle.cache(self._handle_counter)
            elif obj.Handle.get() in self._handles:
                msg = f"Handle {obj.Handle.get()} already exists"
                raise ValueError(msg)
            self._handles.add(obj.Handle.get())

        await self._adapter.update_uuids()

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def UnregisterApplication(self, application: str) -> None:
        sender = sdbus.get_current_message().sender
        logger.debug(f"Client {sender} requested to unregister GATT application {application}")
        assert sender is not None, "D-Bus message sender is None"
        if app := self.apps.get((sender, application)):
            await self.__del_gatt_application(app)
            return
        msg = "Does Not Exist"
        raise DBusBluezDoesNotExistError(msg)
