# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

from typing import Any

import sdbus

from ..utils import dbus_method_async, dbus_property_async


class AdapterInterface(sdbus.DbusInterfaceCommonAsync,
                       interface_name="org.bluez.Adapter1"):

    @dbus_method_async()
    async def StartDiscovery(self) -> None:
        raise NotImplementedError

    @dbus_method_async()
    async def StopDiscovery(self) -> None:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="a{sv}",
        input_args_names=("properties",))
    async def SetDiscoveryFilter(self, properties: dict[str, tuple[str, Any]]) -> None:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="o",
        input_args_names=("device",))
    async def RemoveDevice(self, device: str) -> None:
        raise NotImplementedError

    @dbus_property_async("s")
    def Address(self) -> str:
        raise NotImplementedError

    @dbus_property_async("s")
    def AddressType(self) -> str:
        raise NotImplementedError

    @dbus_property_async("s")
    def Name(self) -> str:
        raise NotImplementedError

    @dbus_property_async("s")
    def Alias(self) -> str:
        raise NotImplementedError

    @dbus_property_async("u")
    def Class(self) -> int:
        raise NotImplementedError

    @dbus_property_async("b")
    def Powered(self) -> bool:
        raise NotImplementedError

    @dbus_property_async("b")
    def Discoverable(self) -> bool:
        raise NotImplementedError

    @dbus_property_async("u")
    def DiscoverableTimeout(self) -> int:
        raise NotImplementedError

    @dbus_property_async("b")
    def Pairable(self) -> bool:
        raise NotImplementedError

    @dbus_property_async("u")
    def PairableTimeout(self) -> int:
        raise NotImplementedError

    @dbus_property_async("b")
    def Discovering(self) -> bool:
        raise NotImplementedError

    @dbus_property_async("as")
    def UUIDs(self) -> list[str]:
        raise NotImplementedError

    @dbus_property_async("as")
    def Roles(self) -> list[str]:
        raise NotImplementedError
