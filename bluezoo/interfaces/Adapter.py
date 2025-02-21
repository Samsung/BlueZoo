# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import asyncio
import logging
import random
from typing import Any

import sdbus

from ..helpers import dbus_method_async, dbus_property_async

# List of predefined device names.
TEST_NAMES = (
    "Alligator's Android",
    "Bobcat's Bluetooth",
    "Eagle's Earbuds",
    "Lion's Laptop",
    "MacBook Pro",
    "ThinkPad",
)


class AdapterInterface(sdbus.DbusInterfaceCommonAsync,
                       interface_name="org.bluez.Adapter1"):

    def __init__(self, service, id: int, address: str, name: str = None):
        super().__init__()

        self.service = service
        self.devices = {}

        self.id = id
        self.address = address
        self.class_ = 0
        self.powered = False
        self.discoverable = False
        self.discoverable_timeout = 180
        self.discoverable_task = None
        self.discovering = False
        self.name = name or random.choice(TEST_NAMES)
        self.alias = self.name

    def get_object_path(self):
        return f"/org/bluez/hci{self.id}"

    async def add_device(self, device):
        device.adapter = self  # Set the device's adapter.
        path = device.get_object_path()
        if path in self.devices:
            return
        logging.info(f"Adding device {device.address} to adapter {self.id}")
        self.service.manager.export_with_manager(path, device, self.service.bus)
        self.devices[path] = device

    async def remove_device(self, device):
        logging.info(f"Removing device {device.address} from adapter {self.id}")
        self.service.manager.remove_managed_object(self.devices.pop(device.get_object_path()))

    @dbus_method_async()
    async def StartDiscovery(self) -> None:
        logging.info(f"Starting discovery on adapter {self.id}")
        self.discovering_task = self.service.create_discovering_task(self.id)
        await self.Discovering.set_async(True)

    @dbus_method_async()
    async def StopDiscovery(self) -> None:
        logging.info(f"Stopping discovery on adapter {self.id}")
        if self.discovering:
            self.discovering_task.cancel()
        await self.Discovering.set_async(False)

    @dbus_method_async(
        input_signature="a{sv}",
        input_args_names=("properties",))
    async def SetDiscoveryFilter(self, properties: dict[str, tuple[str, Any]]) -> None:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="o",
        input_args_names=("device",))
    async def RemoveDevice(self, device: str) -> None:
        self.service.manager.remove_managed_object(self.devices.pop(device))

    @dbus_property_async("s")
    def Address(self) -> str:
        return self.address

    @dbus_property_async("s")
    def AddressType(self) -> str:
        return "public"

    @dbus_property_async("s")
    def Name(self) -> str:
        return self.name

    @dbus_property_async("s")
    def Alias(self) -> str:
        return self.alias

    @Alias.setter
    def Alias_setter(self, value: str):
        self.alias = value

    @dbus_property_async("u")
    def Class(self) -> int:
        return self.class_

    @dbus_property_async("b")
    def Powered(self) -> bool:
        return self.powered

    @Powered.setter
    def Powered_setter(self, value: bool):
        self.powered = value

    @dbus_property_async("b")
    def Discoverable(self) -> bool:
        return self.discoverable

    @Discoverable.setter
    def Discoverable_setter(self, value: bool):
        self.discoverable = value
        if self.discoverable_task is not None:
            self.discoverable_task.cancel()
        if value:
            async def task():
                """Set the adapter as non-discoverable after the timeout."""
                await asyncio.sleep(self.discoverable_timeout)
                await self.Discoverable.set_async(False)
            timeout = self.discoverable_timeout
            logging.info(f"Adapter {self.id} is discoverable for {timeout} seconds")
            self.discoverable_task = asyncio.create_task(task())

    @dbus_property_async("u")
    def DiscoverableTimeout(self) -> int:
        return self.discoverable_timeout

    @DiscoverableTimeout.setter
    def DiscoverableTimeout_setter(self, value: int):
        self.discoverable_timeout = value

    @dbus_property_async("b")
    def Discovering(self) -> bool:
        return self.discovering

    @Discovering.setter
    def Discovering_setter(self, value: bool):
        self.discovering = value
