# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import asyncio

import sdbus
from sdbus.utils import parse_get_managed_objects

from ..log import logger
from ..utils import DBusClientMixin, NoneTask


class GattApplicationClient(DBusClientMixin, sdbus.DbusObjectManagerInterfaceAsync):
    """D-Bus client for registered GATT application."""

    def __init__(self, service, path, options, service_lost_callback):
        super().__init__(service, path, service_lost_callback)
        # Use service lost callback also in case of interface removed.
        self.interfaces_removed_callback = service_lost_callback
        self.options = options

        self.objects: dict[str, DBusClientMixin] = {}
        self.interfaces_removed_task = NoneTask()

    async def cleanup(self):
        for obj in self.objects.values():
            await obj.cleanup()
        self.interfaces_removed_task.cancel()

    async def object_manager_setup_sync_task(self, interfaces):
        """Synchronize cached objects with the D-Bus service."""

        client = self.get_client()
        response_data = await self.get_managed_objects()
        objects = parse_get_managed_objects(
            interfaces,
            response_data,
            on_unknown_interface="none",
            on_unknown_member="ignore")

        for path, (iface, values) in objects.items():
            if iface not in interfaces:
                continue
            obj: DBusClientMixin = iface(client, path)
            await obj.properties_setup_sync_task()
            self.objects[path] = obj

        async def catch_interfaces_removed():
            async for path, _ in self.interfaces_removed.catch():
                if self.objects.pop(path, None):
                    logger.debug("Object removed from GATT application %s", path)
                    await self.interfaces_removed_callback()

        self.interfaces_removed_task = asyncio.create_task(catch_interfaces_removed())
