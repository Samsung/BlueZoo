# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

from typing import Any

import sdbus

from ..helpers import dbus_method_async, dbus_property_async


class DeviceInterface(sdbus.DbusInterfaceCommonAsync,
                      interface_name="org.bluez.Device1"):

    def __init__(self, device):
        self.device = device
        super().__init__()

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
        return self.device.address

    @dbus_property_async("s")
    def AddressType(self) -> str:
        return "public"

    @dbus_property_async("s")
    def Name(self) -> str:
        return self.device.name_

    @dbus_property_async("s")
    def Alias(self) -> str:
        return self.device.name

    @Alias.setter
    def Alias_setter(self, value: str):
        self.device.name = value

    @dbus_property_async("u")
    def Class(self) -> int:
        return self.device.class_

    @dbus_property_async("q")
    def Appearance(self) -> int:
        return self.device.appearance

    @dbus_property_async("as")
    def UUIDs(self) -> list[str]:
        return self.device.uuids

    @dbus_property_async("b")
    def Paired(self) -> bool:
        return self.device.paired

    @dbus_property_async("b")
    def Bonded(self) -> bool:
        return self.device.bonded

    @dbus_property_async("b")
    def Trusted(self) -> bool:
        return self.device.trusted

    @Trusted.setter
    def Trusted_setter(self, value: bool):
        self.device.trusted = value

    @dbus_property_async("b")
    def Blocked(self) -> bool:
        return self.device.blocked

    @Blocked.setter
    def Blocked_setter(self, value: bool):
        self.device.blocked = value

    @dbus_property_async("b")
    def Connected(self) -> bool:
        return self.device.connected

    @dbus_property_async("o")
    def Adapter(self) -> str:
        return self.device.peer.get_object_path()

    @dbus_property_async("a{sv}")
    def ServiceData(self) -> dict[str, tuple[str, Any]]:
        return self.device.service_data

    @dbus_property_async("b")
    def ServicesResolved(self) -> bool:
        return self.device.services_resolved
