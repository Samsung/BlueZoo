# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

from typing import Any

import sdbus

from ..utils import dbus_method_async, dbus_property_async


class LEAdvertisingManagerInterface(sdbus.DbusInterfaceCommonAsync,
                                    interface_name="org.bluez.LEAdvertisingManager1"):

    @dbus_method_async(
        input_signature="oa{sv}",
        input_args_names=("advertisement", "options"))
    async def RegisterAdvertisement(self, advertisement: str,
                                    options: dict[str, tuple[str, Any]]) -> None:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="o",
        input_args_names=("advertisement",))
    async def UnregisterAdvertisement(self, advertisement: str) -> None:
        raise NotImplementedError

    @dbus_property_async("y")
    def ActiveInstances(self) -> int:
        raise NotImplementedError

    @dbus_property_async("y")
    def SupportedInstances(self) -> int:
        raise NotImplementedError

    @dbus_property_async("as")
    def SupportedIncludes(self) -> list[str]:
        raise NotImplementedError

    @dbus_property_async("as")
    def SupportedSecondaryChannels(self) -> list[str]:
        raise NotImplementedError

    @dbus_property_async("a{sv}")
    def SupportedCapabilities(self) -> dict[str, tuple[str, Any]]:
        raise NotImplementedError

    @dbus_property_async("as")
    def SupportedFeatures(self) -> list[str]:
        raise NotImplementedError
