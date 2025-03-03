# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import sdbus

from ..utils import dbus_property_async


class GattServiceInterface(sdbus.DbusInterfaceCommonAsync,
                           interface_name="org.bluez.GattService1"):

    @dbus_property_async("s")
    def UUID(self) -> str:
        raise NotImplementedError

    @dbus_property_async("b")
    def Primary(self) -> bool:
        raise NotImplementedError

    @dbus_property_async("o")
    def Device(self) -> str:
        raise NotImplementedError

    @dbus_property_async("ao")
    def Includes(self) -> list[str]:
        raise NotImplementedError

    @dbus_property_async("q")
    def Handle(self) -> int:
        raise NotImplementedError
