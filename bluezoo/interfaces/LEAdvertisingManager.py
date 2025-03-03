# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import logging
from typing import Any

import sdbus

from ..utils import DBusClientMixin, dbus_method_async, dbus_property_async
from .LEAdvertisement import LEAdvertisementInterface


class LEAdvertisement(DBusClientMixin, LEAdvertisementInterface):
    """D-Bus client for the LEAdvertisement1 interface."""

    def __init__(self, service, path, options):
        super().__init__(service, path)
        self.options = options


class LEAdvertisingManagerInterface(sdbus.DbusInterfaceCommonAsync,
                                    interface_name="org.bluez.LEAdvertisingManager1"):

    advertisements = None
    advertisement_slots_active: int = None
    advertisement_slots_available: int = None

    async def add_le_advertisement(self, advertisement: LEAdvertisement) -> None:
        raise NotImplementedError

    async def del_le_advertisement(self, advertisement: LEAdvertisement) -> None:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="oa{sv}",
        input_args_names=("advertisement", "options"))
    async def RegisterAdvertisement(self, advertisement: str,
                                    options: dict[str, tuple[str, Any]]) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to register advertisement {advertisement}")
        advertisement = LEAdvertisement(sender, advertisement, options)
        await advertisement.properties_setup_sync_task()
        await self.add_le_advertisement(advertisement)

    @dbus_method_async(
        input_signature="o",
        input_args_names=("advertisement",))
    async def UnregisterAdvertisement(self, advertisement: str) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to unregister advertisement {advertisement}")
        await self.del_le_advertisement(self.advertisements[sender, advertisement])

    @dbus_property_async("y")
    def ActiveInstances(self) -> int:
        return self.advertisement_slots_active

    @ActiveInstances.setter_private
    def ActiveInstances_setter(self, value: int) -> None:
        pass

    @dbus_property_async("y")
    def SupportedInstances(self) -> int:
        return self.advertisement_slots_available

    @SupportedInstances.setter_private
    def SupportedInstances_setter(self, value: int) -> None:
        pass

    @dbus_property_async("as")
    def SupportedIncludes(self) -> list[str]:
        return ["tx-power", "appearance", "local-name"]

    @dbus_property_async("as")
    def SupportedSecondaryChannels(self) -> list[str]:
        return ["1M"]

    @dbus_property_async("a{sv}")
    def SupportedCapabilities(self) -> dict[str, tuple[str, Any]]:
        caps = {}
        caps["MaxAdvLen"] = ("y", 31)
        caps["MaxScanRespLen"] = ("y", 31)
        return caps

    @dbus_property_async("as")
    def SupportedFeatures(self) -> list[str]:
        return []
