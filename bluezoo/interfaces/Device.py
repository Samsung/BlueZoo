# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

from typing import Any

import sdbus

from ..utils import (dbus_method_async, dbus_method_async_except_logging, dbus_property_async,
                     dbus_property_async_except_logging)


class DeviceInterface(sdbus.DbusInterfaceCommonAsync,
                      interface_name="org.bluez.Device1"):

    async def connect(self, uuid: str = None) -> None:
        raise NotImplementedError

    async def disconnect(self, uuid: str = None) -> None:
        raise NotImplementedError

    async def pair(self) -> None:
        raise NotImplementedError

    async def cancel_pairing(self) -> None:
        raise NotImplementedError

    @dbus_method_async()
    @dbus_method_async_except_logging
    async def Connect(self) -> None:
        await self.connect()

    @dbus_method_async()
    @dbus_method_async_except_logging
    async def Disconnect(self) -> None:
        await self.disconnect()

    @dbus_method_async(
        input_signature="s",
        input_args_names=("uuid",))
    @dbus_method_async_except_logging
    async def ConnectProfile(self, uuid: str) -> None:
        await self.connect(uuid)

    @dbus_method_async(
        input_signature="s",
        input_args_names=("uuid",))
    @dbus_method_async_except_logging
    async def DisconnectProfile(self, uuid: str) -> None:
        await self.disconnect(uuid)

    @dbus_method_async()
    @dbus_method_async_except_logging
    async def Pair(self) -> None:
        await self.pair()

    @dbus_method_async()
    @dbus_method_async_except_logging
    async def CancelPairing(self) -> None:
        await self.cancel_pairing()

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

    @Name.setter_private
    def Name_setter(self, value: str):
        self.name_ = value

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

    @dbus_property_async("q")
    @dbus_property_async_except_logging
    def Appearance(self) -> int:
        return self.appearance

    @Appearance.setter_private
    def Appearance_setter(self, value: int):
        self.appearance = value

    @dbus_property_async("as")
    @dbus_property_async_except_logging
    def UUIDs(self) -> list[str]:
        return self.uuids

    @UUIDs.setter_private
    def UUIDs_setter(self, value: list[str]):
        self.uuids = value

    @dbus_property_async("b")
    @dbus_property_async_except_logging
    def Paired(self) -> bool:
        return self.paired

    @Paired.setter_private
    def Paired_setter(self, value: bool):
        self.paired = value

    @dbus_property_async("b")
    @dbus_property_async_except_logging
    def Bonded(self) -> bool:
        return self.bonded

    @Bonded.setter_private
    def Bonded_setter(self, value: bool):
        self.bond = value

    @dbus_property_async("b")
    @dbus_property_async_except_logging
    def Trusted(self) -> bool:
        return self.trusted

    @Trusted.setter
    def Trusted_setter(self, value: bool):
        self.trusted = value

    @dbus_property_async("b")
    @dbus_property_async_except_logging
    def Blocked(self) -> bool:
        return self.blocked

    @Blocked.setter
    def Blocked_setter(self, value: bool):
        self.blocked = value

    @dbus_property_async("b")
    @dbus_property_async_except_logging
    def Connected(self) -> bool:
        return self.connected

    @Connected.setter_private
    def Connected_setter(self, value: bool):
        self.connected = value

    @dbus_property_async("o")
    @dbus_property_async_except_logging
    def Adapter(self) -> str:
        return self.adapter.get_object_path()

    @dbus_property_async("a{sv}")
    @dbus_property_async_except_logging
    def ServiceData(self) -> dict[str, tuple[str, Any]]:
        return self.service_data

    @ServiceData.setter_private
    def ServiceData_setter(self, value: dict[str, tuple[str, Any]]):
        self.service_data = value

    @dbus_property_async("b")
    @dbus_property_async_except_logging
    def ServicesResolved(self) -> bool:
        return self.services_resolved

    @ServicesResolved.setter_private
    def ServicesResolved_setter(self, value: bool):
        self.services_resolved = value
