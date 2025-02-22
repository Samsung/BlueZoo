# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

from typing import Any

import sdbus

from ..helpers import dbus_method_async, dbus_property_async


class AdapterInterface(sdbus.DbusInterfaceCommonAsync,
                       interface_name="org.bluez.Adapter1"):

    def __init__(self, controller):
        self.controller = controller
        super().__init__()

    @dbus_method_async()
    async def StartDiscovery(self) -> None:
        await self.controller.start_discovering()

    @dbus_method_async()
    async def StopDiscovery(self) -> None:
        await self.controller.stop_discovering()

    @dbus_method_async(
        input_signature="a{sv}",
        input_args_names=("properties",))
    async def SetDiscoveryFilter(self, properties: dict[str, tuple[str, Any]]) -> None:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="o",
        input_args_names=("device",))
    async def RemoveDevice(self, device: str) -> None:
        if device not in self.controller.devices:
            return
        self.controller.remove_device(self.controller.devices[device])

    @dbus_property_async("s")
    def Address(self) -> str:
        return self.controller.address

    @dbus_property_async("s")
    def AddressType(self) -> str:
        return "public"

    @dbus_property_async("s")
    def Name(self) -> str:
        return self.controller.name_

    @dbus_property_async("s")
    def Alias(self) -> str:
        return self.controller.name

    @Alias.setter
    def Alias_setter(self, value: str):
        self.controller.name = value

    @dbus_property_async("u")
    def Class(self) -> int:
        return self.controller.class_

    @dbus_property_async("b")
    def Powered(self) -> bool:
        return self.controller.powered

    @Powered.setter
    def Powered_setter(self, value: bool):
        self.controller.powered = value

    @dbus_property_async("b")
    def Discoverable(self) -> bool:
        return self.controller.discoverable

    @Discoverable.setter
    def Discoverable_setter(self, value: bool):
        self.controller.set_discoverable(value)

    @dbus_property_async("u")
    def DiscoverableTimeout(self) -> int:
        return self.controller.discoverable_timeout

    @DiscoverableTimeout.setter
    def DiscoverableTimeout_setter(self, value: int):
        self.controller.discoverable_timeout = value

    @dbus_property_async("b")
    def Pairable(self) -> bool:
        return self.controller.pairable

    @Pairable.setter
    def Pairable_setter(self, value: bool):
        self.controller.set_pairable(value)

    @dbus_property_async("u")
    def PairableTimeout(self) -> int:
        return self.controller.pairable_timeout

    @PairableTimeout.setter
    def PairableTimeout_setter(self, value: int):
        self.controller.pairable_timeout = value

    @dbus_property_async("b")
    def Discovering(self) -> bool:
        return self.controller.discovering

    @Discovering.setter
    def Discovering_setter(self, value: bool):
        self.controller.discovering = value

    @dbus_property_async("as")
    def UUIDs(self) -> list[str]:
        return self.controller.uuids

    @dbus_property_async("as")
    def Roles(self) -> list[str]:
        return ["central", "peripheral"]
