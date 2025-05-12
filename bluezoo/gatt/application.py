# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import asyncio
import weakref

import sdbus
from sdbus.utils import parse_get_managed_objects

from ..utils import DBusClientMixin


class GattApplicationClient(DBusClientMixin, sdbus.DbusObjectManagerInterfaceAsync):
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

        client = self.get_client()
        response_data = await self.get_managed_objects()
        objects = parse_get_managed_objects(
            interfaces,
            response_data,
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
