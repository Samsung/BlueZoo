# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

from typing import Any

import sdbus

from ..helpers import dbus_method_async, dbus_property_async


class DeviceInterface(sdbus.DbusInterfaceCommonAsync,
                      interface_name="org.bluez.Device1"):

    def __init__(self, address: str, name: str):
        super().__init__()

        self.adapter = None

        self.address = address
        self.class_ = 0
        self.appearance = 0
        self.paired = False
        self.bonded = False
        self.trusted = False
        self.blocked = False
        self.connected = False
        self.services_resolved = False
        self.service_data = {}
        self.name = name
        self.alias = name
        self.uuids = []

    def get_object_path(self):
        return "/".join((
            self.adapter.get_object_path(),
            f"dev_{self.address.replace(':', '_')}"))

    @dbus_method_async()
    async def Disconnect(self) -> None:
        raise NotImplementedError

    @dbus_method_async()
    async def Connect(self) -> None:
        raise NotImplementedError

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

    @dbus_property_async("q")
    def Appearance(self) -> int:
        return self.appearance

    @dbus_property_async("as")
    def UUIDs(self) -> list[str]:
        return self.uuids

    @dbus_property_async("b")
    def Paired(self) -> bool:
        return self.paired

    @dbus_property_async("b")
    def Bonded(self) -> bool:
        return self.bonded

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
        return self.adapter.get_object_path()

    @dbus_property_async("a{sv}")
    def ServiceData(self) -> dict[str, tuple[str, Any]]:
        return self.service_data

    @dbus_property_async("b")
    def ServicesResolved(self) -> bool:
        return self.services_resolved
