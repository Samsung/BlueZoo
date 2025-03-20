# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

from typing import Any

import sdbus

from ..utils import dbus_method_async, dbus_property_async


class DeviceInterface(sdbus.DbusInterfaceCommonAsync,
                      interface_name="org.bluez.Device1"):

    @dbus_method_async()
    async def Connect(self) -> None:
        raise NotImplementedError

    @dbus_method_async()
    async def Disconnect(self) -> None:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="s",
        input_args_names=("uuid",))
    async def ConnectProfile(self, uuid: str) -> None:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="s",
        input_args_names=("uuid",))
    async def DisconnectProfile(self, uuid: str) -> None:
        raise NotImplementedError

    @dbus_method_async()
    async def Pair(self) -> None:
        raise NotImplementedError

    @dbus_method_async()
    async def CancelPairing(self) -> None:
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

    @dbus_property_async("q")
    def Appearance(self) -> int:
        raise NotImplementedError

    @dbus_property_async("as")
    def UUIDs(self) -> list[str]:
        raise NotImplementedError

    @dbus_property_async("b")
    def Paired(self) -> bool:
        raise NotImplementedError

    @dbus_property_async("b")
    def Bonded(self) -> bool:
        raise NotImplementedError

    @dbus_property_async("b")
    def Trusted(self) -> bool:
        raise NotImplementedError

    @dbus_property_async("b")
    def Blocked(self) -> bool:
        raise NotImplementedError

    @dbus_property_async("b")
    def Connected(self) -> bool:
        raise NotImplementedError

    @dbus_property_async("o")
    def Adapter(self) -> str:
        raise NotImplementedError

    @dbus_property_async("a{sv}")
    def ServiceData(self) -> dict[str, tuple[str, Any]]:
        raise NotImplementedError

    @dbus_property_async("b")
    def ServicesResolved(self) -> bool:
        raise NotImplementedError
