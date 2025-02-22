# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import asyncio
import logging

from sdbus import DbusObjectManagerInterfaceAsync

from .interfaces import AdapterInterface, AgentManagerInterface, DeviceInterface


class BluezMockService:

    def __init__(self, bus):
        self.manager = DbusObjectManagerInterfaceAsync()
        self.manager.export_to_dbus("/", bus)
        self.adapters = {}
        self.bus = bus

    def add_adapter(self, id: int, address: str):
        logging.info(f"Adding adapter {id} with address {address}")
        adapter = AdapterInterface(self, id, address)
        agent_manager = AgentManagerInterface(self)
        path = adapter.get_object_path()
        self.manager.export_with_manager(path, adapter, self.bus)
        self.manager.export_with_manager(path, agent_manager, self.bus)
        self.adapters[id] = [adapter, agent_manager]

    def del_adapter(self, id: int):
        logging.info(f"Removing adapter {id}")
        for interface in self.adapters.pop(id):
            self.manager.remove_managed_object(interface)

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
                    if not adapter.powered or not adapter.discoverable:
                        continue
                    # Report the device (adapter) on our adapter.
                    await self.adapters[id].add_device(DeviceInterface(
                        address=adapter.address,
                        name=adapter.alias))
                await asyncio.sleep(10)
        return asyncio.create_task(task())
