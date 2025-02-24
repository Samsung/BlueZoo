# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

from typing import Any

import sdbus

from ..helpers import dbus_method_async, dbus_property_async


class DeviceInterface(sdbus.DbusInterfaceCommonAsync,
                      interface_name="org.bluez.Device1"):

    async def pair(self) -> None:
        raise NotImplementedError

    async def cancel_pairing(self) -> None:
        raise NotImplementedError

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
        await self.pair()

    @dbus_method_async()
    async def CancelPairing(self) -> None:
        await self.cancel_pairing()

    @dbus_property_async("s")
    def Address(self) -> str:
        return self.address

    @dbus_property_async("s")
    def AddressType(self) -> str:
        return "public"

    @dbus_property_async("s")
    def Name(self) -> str:
        return self.name_

    @dbus_property_async("s")
    def Alias(self) -> str:
        return self.name

    @Alias.setter
    def Alias_setter(self, value: str):
        self.name = value

    @dbus_property_async("u")
    def Class(self) -> int:
        return self.class_

    @dbus_property_async("q")
    def Appearance(self) -> int:
        return self.appearance

    @dbus_property_async("as")
    def UUIDs(self) -> list[str]:
        return self.uuids

    @dbus_property_async("b")
    def Paired(self) -> bool:
        return self.paired

    @Paired.setter_private
    def Paired_setter(self, value: bool):
        self.paired = value

    @dbus_property_async("b")
    def Bonded(self) -> bool:
        return self.bonded

    @Bonded.setter_private
    def Bonded_setter(self, value: bool):
        self.bond = value

    @dbus_property_async("b")
    def Trusted(self) -> bool:
        return self.trusted

    @Trusted.setter
    def Trusted_setter(self, value: bool):
        self.trusted = value

    @dbus_property_async("b")
    def Blocked(self) -> bool:
        return self.blocked

    @Blocked.setter
    def Blocked_setter(self, value: bool):
        self.blocked = value

    @dbus_property_async("b")
    def Connected(self) -> bool:
        return self.connected

    @dbus_property_async("o")
    def Adapter(self) -> str:
        return self.peer.get_object_path()

    @dbus_property_async("a{sv}")
    def ServiceData(self) -> dict[str, tuple[str, Any]]:
        return self.service_data

    @dbus_property_async("b")
    def ServicesResolved(self) -> bool:
        return self.services_resolved
