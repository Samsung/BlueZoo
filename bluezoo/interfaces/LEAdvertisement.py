# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

from typing import Any

import sdbus

from ..helpers import dbus_method_async, dbus_property_async


class LEAdvertisementInterface(sdbus.DbusInterfaceCommonAsync,
                               interface_name="org.bluez.LEAdvertisement1"):

    @dbus_method_async()
    async def Release(self) -> None:
        raise NotImplementedError

    @dbus_property_async("s")
    def Type(self) -> str:
        raise NotImplementedError

    @dbus_property_async("as")
    def ServiceUUIDs(self) -> list[str]:
        raise NotImplementedError

    @dbus_property_async("a{qv}")
    def ManufacturerData(self) -> dict[int, tuple[str, Any]]:
        raise NotImplementedError

    @dbus_property_async("as")
    def SolicitUUIDs(self) -> list[str]:
        raise NotImplementedError

    @dbus_property_async("a{sv}")
    def ServiceData(self) -> dict[str, tuple[str, Any]]:
        raise NotImplementedError

    @dbus_property_async("a{yay}")
    def Data(self) -> dict[int, bytes]:
        raise NotImplementedError

    @dbus_property_async("as")
    def ScanResponseServiceUUIDs(self) -> list[str]:
        raise NotImplementedError

    @dbus_property_async("a{yay}")
    def ScanResponseManufacturerData(self) -> dict[int, bytes]:
        raise NotImplementedError

    @dbus_property_async("as")
    def ScanResponseSolicitUUIDs(self) -> list[str]:
        raise NotImplementedError

    @dbus_property_async("a{say}")
    def ScanResponseServiceData(self) -> dict[str, bytes]:
        raise NotImplementedError

    @dbus_property_async("a{yay}")
    def ScanResponseData(self) -> dict[int, bytes]:
        raise NotImplementedError

    @dbus_property_async("b")
    def Discoverable(self) -> bool:
        raise NotImplementedError

    @dbus_property_async("q")
    def DiscoverableTimeout(self) -> int:
        raise NotImplementedError

    @dbus_property_async("as")
    def Includes(self) -> list[str]:
        raise NotImplementedError

    @dbus_property_async("s")
    def LocalName(self) -> str:
        raise NotImplementedError

    @dbus_property_async("q")
    def Appearance(self) -> int:
        raise NotImplementedError

    @dbus_property_async("q")
    def Duration(self) -> int:
        raise NotImplementedError

    @dbus_property_async("q")
    def Timeout(self) -> int:
        raise NotImplementedError

    @dbus_property_async("s")
    def SecondaryChannel(self) -> str:
        raise NotImplementedError

    @dbus_property_async("u")
    def MinInterval(self) -> int:
        raise NotImplementedError

    @dbus_property_async("u")
    def MaxInterval(self) -> int:
        raise NotImplementedError

    @dbus_property_async("n")
    def TxPower(self) -> int:
        raise NotImplementedError
