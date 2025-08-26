# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import asyncio
from enum import StrEnum
from typing import Any

import sdbus

from . import events
from .adv import LEAdvertisingManager
from .device import Device
from .gatt import GattManager
from .interfaces.Adapter import AdapterInterface
from .log import logger
from .utils import (BluetoothClass, BluetoothUUID, NoneTask, create_background_task,
                    dbus_method_async_except_logging, dbus_property_async_except_logging)

# List of predefined device names.
TEST_NAMES = (
    "Alligator's Android",
    "Bobcat's Bluetooth",
    "Eagle's Earbuds",
    "Lion's Laptop",
    "MacBook Pro",
    "ThinkPad",
)


class Adapter(LEAdvertisingManager, GattManager, AdapterInterface):

    class PowerStateValue(StrEnum):
        On = "on"
        Off = "off"
        OffEnabling = "off-enabling"
        OnDisabling = "on-disabling"
        OffBlocked = "off-blocked"

    def __init__(self, mock, id: int, address: str):
        super().__init__()
        self.mock = mock

        self.id = id
        self.address = address
        self.name_ = TEST_NAMES[id % len(TEST_NAMES)]
        self.class_ = BluetoothClass(BluetoothClass.Major.Computer)
        self.powered = False
        self.connectable = False
        self.discoverable = False
        self.discoverable_timeout = 180
        self.discoverable_task = NoneTask()
        self.pairable = False
        self.pairable_timeout = 0
        self.pairable_task = NoneTask()
        self.discovering = False
        self.discovering_task = NoneTask()
        self.uuids: list[str] = []

        self.scan_subscribers = {}
        self.scan_filter_uuids: list[str] = []
        self.scan_filter_transport = "auto"
        self.scan_filter_duplicate = False
        self.scan_filter_discoverable = False
        self.scan_filter_pattern = None

        self.devices: dict[str, Device] = {}

    def __str__(self):
        return f"adapter[{self.id}][{self.address}]"

    async def cleanup(self):
        await LEAdvertisingManager.cleanup(self)
        await GattManager.cleanup(self)
        self.discoverable_task.cancel()
        self.pairable_task.cancel()
        self.discovering_task.cancel()

    def get_object_path(self):
        return f"/org/bluez/hci{self.id}"

    @property
    def name(self):
        return getattr(self, "name__", self.name_)

    @name.setter
    def name(self, value):
        self.name__ = value

    async def update_uuids(self):
        uuids = set()
        uuids.update(self.get_gatt_registered_primary_services())
        await self.UUIDs.set_async(list(uuids))

    async def add_device(self, device: Device):
        device.attach_to_adapter(self)
        path = device.get_object_path()
        if path in self.devices:
            logger.debug(f"Updating {device} in {self}")
            await self.devices[path].properties_sync(device)
            return
        logger.info(f"Adding {device} to {self}")
        self.mock.manager.export_with_manager(path, device)
        self.devices[path] = device

    async def del_device(self, device: Device):
        await device.disconnect()
        logger.info(f"Removing {device} from {self}")
        self.devices.pop(device.get_object_path())
        self.mock.manager.remove_managed_object(device)
        await device.cleanup()

    async def __stop_discovering(self):
        logger.info(f"Stopping discovery on {self}")
        self.discovering_task.cancel()
        await self.Discovering.set_async(False)

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def StartDiscovery(self) -> None:
        sender = sdbus.get_current_message().sender
        logger.info(f"Starting discovery on {self}")

        async def on_sender_lost():
            self.scan_subscribers.pop(sender, None)
            if not self.scan_subscribers:
                await self.__stop_discovering()
        self.scan_subscribers[sender] = events.subscribe(f"service:lost:{sender}",
                                                         on_sender_lost, once=True)

        self.discovering_task = self.mock.create_discovering_task(self.id)
        await self.Discovering.set_async(True)

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def StopDiscovery(self) -> None:
        sender = sdbus.get_current_message().sender
        if subscriber := self.scan_subscribers.pop(sender, None):
            subscriber.unsubscribe()
        await self.__stop_discovering()

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def SetDiscoveryFilter(self, properties: dict[str, tuple[str, Any]]) -> None:
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

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def GetDiscoveryFilters(self) -> list[str]:
        return ["UUIDs", "RSSI", "Pathloss", "Transport", "DuplicateData",
                "Discoverable", "Pattern"]

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def RemoveDevice(self, device: str) -> None:
        if device not in self.devices:
            return
        await self.del_device(self.devices[device])

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Address(self) -> str:
        return self.address

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def AddressType(self) -> str:
        return "public"

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Name(self) -> str:
        return self.name_

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Alias(self) -> str:
        return self.name

    @Alias.setter
    def Alias_setter(self, value: str):
        self.name = value

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Class(self) -> int:
        return self.class_

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Powered(self) -> bool:
        return self.powered

    @Powered.setter
    def Powered_setter(self, value: bool):

        async def off():
            await self.PowerState.set_async(Adapter.PowerStateValue.OnDisabling)
            await self.PowerState.set_async(Adapter.PowerStateValue.Off)
            await self.__stop_discovering()

        async def on():
            await self.PowerState.set_async(Adapter.PowerStateValue.OffEnabling)
            await self.PowerState.set_async(Adapter.PowerStateValue.On)

        if self.powered != value:
            create_background_task(on() if value else off())
            self.powered = value

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def PowerState(self) -> str:
        if self.powered:
            return Adapter.PowerStateValue.On
        return Adapter.PowerStateValue.Off

    @PowerState.setter_private
    def PowerState_setter(self, value: str):
        pass

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Connectable(self) -> bool:
        return self.connectable

    @Connectable.setter
    def Connectable_setter(self, value: bool):
        if not value:
            create_background_task(self.Discoverable.set_async(False))
        self.connectable = value

    def __setup_discoverable_timeout(self):
        self.discoverable_task.cancel()
        if self.discoverable:
            async def task():
                """Set the adapter as non-discoverable after the timeout."""
                await asyncio.sleep(self.discoverable_timeout)
                await self.Discoverable.set_async(False)
            # If timeout is non-zero, set up cancellation task.
            if timeout := self.discoverable_timeout:
                logger.info(f"Setting {self} as discoverable for {timeout} seconds")
                self.discoverable_task = asyncio.create_task(task())

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Discoverable(self) -> bool:
        return self.discoverable

    @Discoverable.setter
    def Discoverable_setter(self, value: bool):
        self.discoverable = value
        self.__setup_discoverable_timeout()

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def DiscoverableTimeout(self) -> int:
        return self.discoverable_timeout

    @DiscoverableTimeout.setter
    def DiscoverableTimeout_setter(self, value: int):
        self.discoverable_timeout = value
        self.__setup_discoverable_timeout()

    def __setup_pairable_timeout(self):
        self.pairable_task.cancel()
        if self.pairable:
            async def task():
                """Set the adapter as non-pairable after the timeout."""
                await asyncio.sleep(self.pairable_timeout)
                await self.Pairable.set_async(False)
            # If timeout is non-zero, set up cancellation task.
            if timeout := self.pairable_timeout:
                logger.info(f"Setting {self} as pairable for {timeout} seconds")
                self.pairable_task = asyncio.create_task(task())

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Pairable(self) -> bool:
        return self.pairable

    @Pairable.setter
    def Pairable_setter(self, value: bool):
        self.pairable = value
        self.__setup_pairable_timeout()

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def PairableTimeout(self) -> int:
        return self.pairable_timeout

    @PairableTimeout.setter
    def PairableTimeout_setter(self, value: int):
        self.pairable_timeout = value
        self.__setup_pairable_timeout()

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Discovering(self) -> bool:
        return self.discovering

    @Discovering.setter
    def Discovering_setter(self, value: bool):
        self.discovering = value

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def UUIDs(self) -> list[str]:
        return self.uuids

    @UUIDs.setter_private
    def UUIDs_setter(self, value: list[str]):
        self.uuids = value

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Modalias(self) -> str:
        return "usb:v1D6Bp0246d0537"

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Roles(self) -> list[str]:
        return ["central", "peripheral", "central-peripheral"]

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def ExperimentalFeatures(self) -> list[str]:
        return []

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Manufacturer(self) -> int:
        return 0x05F1

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Version(self) -> int:
        return 0x06
