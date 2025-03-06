# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

from typing import Any

import sdbus

from ..utils import (dbus_method_async, dbus_method_async_except_logging, dbus_property_async,
                     dbus_property_async_except_logging)


class AdapterInterface(sdbus.DbusInterfaceCommonAsync,
                       interface_name="org.bluez.Adapter1"):

    async def start_discovering(self, client) -> None:
        raise NotImplementedError

    async def stop_discovering(self) -> None:
        raise NotImplementedError

    async def del_device(self, device) -> None:
        raise NotImplementedError

    def set_discovery_filter(self, properties: dict[str, tuple[str, Any]]) -> None:
        raise NotImplementedError

    def set_discoverable(self, enabled: bool) -> None:
        raise NotImplementedError

    def set_pairable(self, enabled: bool) -> None:
        raise NotImplementedError

    @dbus_method_async()
    @dbus_method_async_except_logging
    async def StartDiscovery(self) -> None:
        sender = sdbus.get_current_message().sender
        await self.start_discovering(sender)

    @dbus_method_async()
    @dbus_method_async_except_logging
    async def StopDiscovery(self) -> None:
        await self.stop_discovering()

    @dbus_method_async(
        input_signature="a{sv}",
        input_args_names=("properties",))
    @dbus_method_async_except_logging
    async def SetDiscoveryFilter(self, properties: dict[str, tuple[str, Any]]) -> None:
        self.set_discovery_filter(properties)

    @dbus_method_async(
        input_signature="o",
        input_args_names=("device",))
    @dbus_method_async_except_logging
    async def RemoveDevice(self, device: str) -> None:
        if device not in self.devices:
            return
        await self.del_device(self.devices[device])

    @dbus_property_async("s")
    @dbus_property_async_except_logging
    def Address(self) -> str:
        return self.address

    @dbus_property_async("s")
    @dbus_property_async_except_logging
    def AddressType(self) -> str:
        return "public"

    @dbus_property_async("s")
    @dbus_property_async_except_logging
    def Name(self) -> str:
        return self.name_

    @dbus_property_async("s")
    @dbus_property_async_except_logging
    def Alias(self) -> str:
        return self.name

    @Alias.setter
    def Alias_setter(self, value: str):
        self.name = value

    @dbus_property_async("u")
    @dbus_property_async_except_logging
    def Class(self) -> int:
        return self.class_

    @dbus_property_async("b")
    @dbus_property_async_except_logging
    def Powered(self) -> bool:
        return self.powered

    @Powered.setter
    def Powered_setter(self, value: bool):
        self.powered = value

    @dbus_property_async("b")
    @dbus_property_async_except_logging
    def Discoverable(self) -> bool:
        return self.discoverable

    @Discoverable.setter
    def Discoverable_setter(self, value: bool):
        self.set_discoverable(value)

    @dbus_property_async("u")
    @dbus_property_async_except_logging
    def DiscoverableTimeout(self) -> int:
        return self.discoverable_timeout

    @DiscoverableTimeout.setter
    def DiscoverableTimeout_setter(self, value: int):
        self.discoverable_timeout = value
        self.set_discoverable(self.discoverable)

    @dbus_property_async("b")
    @dbus_property_async_except_logging
    def Pairable(self) -> bool:
        return self.pairable

    @Pairable.setter
    def Pairable_setter(self, value: bool):
        self.set_pairable(value)

    @dbus_property_async("u")
    @dbus_property_async_except_logging
    def PairableTimeout(self) -> int:
        return self.pairable_timeout

    @PairableTimeout.setter
    def PairableTimeout_setter(self, value: int):
        self.pairable_timeout = value
        self.set_pairable(self.pairable)

    @dbus_property_async("b")
    @dbus_property_async_except_logging
    def Discovering(self) -> bool:
        return self.discovering

    @Discovering.setter
    def Discovering_setter(self, value: bool):
        self.discovering = value

    @dbus_property_async("as")
    @dbus_property_async_except_logging
    def UUIDs(self) -> list[str]:
        return self.uuids

    @UUIDs.setter_private
    def UUIDs_setter(self, value: list[str]):
        self.uuids = value

    @dbus_property_async("as")
    @dbus_property_async_except_logging
    def Roles(self) -> list[str]:
        return ["central", "peripheral"]
