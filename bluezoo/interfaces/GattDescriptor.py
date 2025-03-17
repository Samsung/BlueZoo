# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

from typing import Any

import sdbus

from ..utils import dbus_method_async, dbus_property_async


class GattDescriptorInterface(sdbus.DbusInterfaceCommonAsync,
                              interface_name="org.bluez.GattDescriptor1"):

    @dbus_method_async(
        input_signature="a{sv}",
        input_args_names=("options",),
        result_signature="ay",
        result_args_names=('value',))
    async def ReadValue(self, options: dict[str, tuple[str, Any]]) -> bytes:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="aya{sv}",
        input_args_names=("value", "options"))
    async def WriteValue(self, value: bytes, options: dict[str, tuple[str, Any]]) -> None:
        raise NotImplementedError

    @dbus_property_async("s")
    def UUID(self) -> str:
        raise NotImplementedError

    @dbus_property_async("o")
    def Characteristic(self) -> str:
        raise NotImplementedError

    @dbus_property_async("ay")
    def Value(self) -> bytes:
        raise NotImplementedError

    @dbus_property_async("as")
    def Flags(self) -> list[str]:
        raise NotImplementedError

    @dbus_property_async("q")
    def Handle(self) -> int:
        raise NotImplementedError
