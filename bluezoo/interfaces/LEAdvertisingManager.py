# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import logging
from typing import Any

import sdbus

from ..helpers import dbus_method_async, dbus_property_async
from .LEAdvertisement import LEAdvertisementInterface


class LEAdvertisement(LEAdvertisementInterface):
    """D-Bus client for the LEAdvertisement1 interface."""

    def __init__(self, options, client, path, bus):
        super().__init__()
        self.options = options
        self.destination = (client, path)
        self._connect(client, path, bus)


class LEAdvertisingManagerInterface(sdbus.DbusInterfaceCommonAsync,
                                    interface_name="org.bluez.LEAdvertisingManager1"):

    # Number of supported advertisement instances.
    INSTANCES = 15

    def __init__(self, service):
        super().__init__()
        self.service = service
        self.advertisements = {}

    @property
    def active_instances(self):
        return len(self.advertisements)

    @property
    def supported_instances(self):
        return self.INSTANCES - len(self.advertisements)

    @dbus_method_async(
        input_signature="oa{sv}",
        input_args_names=("advertisement", "options"))
    async def RegisterAdvertisement(self, advertisement: str,
                                    options: dict[str, tuple[str, Any]]) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to register advertisement {advertisement}")
        self.advertisements[(sender, advertisement)] = LEAdvertisement(options, sender,
                                                                       advertisement,
                                                                       self.service.bus)
        await self.ActiveInstances.set_async(self.active_instances)
        await self.SupportedInstances.set_async(self.supported_instances)

    @dbus_method_async(
        input_signature="o",
        input_args_names=("advertisement",))
    async def UnregisterAdvertisement(self, advertisement: str) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to unregister advertisement {advertisement}")
        self.advertisements.pop((sender, advertisement))
        await self.ActiveInstances.set_async(self.active_instances)
        await self.SupportedInstances.set_async(self.supported_instances)

    @dbus_property_async("y")
    def ActiveInstances(self) -> int:
        return self.active_instances

    @ActiveInstances.setter_private
    def ActiveInstances_setter(self, value: int) -> None:
        pass

    @dbus_property_async("y")
    def SupportedInstances(self) -> int:
        return self.supported_instances

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
