# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import logging
from typing import Any

import sdbus

from ..exceptions import DBusBluezDoesNotExistError, DBusBluezNotPermittedError
from ..interfaces.LEAdvertisement import LEAdvertisementInterface
from ..interfaces.LEAdvertisingManager import LEAdvertisingManagerInterface
from ..utils import (DBusClientMixin, dbus_method_async_except_logging,
                     dbus_property_async_except_logging)


class LEAdvertisementClient(DBusClientMixin, LEAdvertisementInterface):
    """D-Bus client for LE advertisement."""

    def __init__(self, service, path, options):
        super().__init__(service, path)
        self.options = options

    def __str__(self):
        options = " ".join(f"{k}={v[1]}" for k, v in self.options.items())
        return f"advertisement[{options}]"


class LEAdvertisingManager(LEAdvertisingManagerInterface):
    """Bluetooth Low Energy (BLE) advertising manager."""

    # Number of supported advertisement instances per adapter.
    SUPPORTED_ADVERTISEMENT_INSTANCES = 15

    def __init__(self):
        super().__init__()
        self.advertisements = {}

    @property
    def __supported_instances(self) -> int:
        return self.SUPPORTED_ADVERTISEMENT_INSTANCES - len(self.advertisements)

    async def __del_advertisement(self, adv: LEAdvertisementClient):
        logging.info(f"Removing {adv}")

        self.service.on_client_lost_remove(adv.get_client(), adv.on_client_lost)
        self.advertisements.pop((adv.get_client(), adv.get_object_path()))

        await self.ActiveInstances.set_async(len(self.advertisements))
        await self.SupportedInstances.set_async(self.__supported_instances)

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def RegisterAdvertisement(self, path: str,
                                    options: dict[str, tuple[str, Any]]) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to register advertisement {path}")

        if not self.__supported_instances:
            raise DBusBluezNotPermittedError("Not Permitted")

        adv = LEAdvertisementClient(sender, path, options)
        await adv.properties_setup_sync_task()

        logging.info(f"Registering {adv}")
        self.advertisements[sender, path] = adv

        async def on_client_lost():
            await self.__del_advertisement(adv)
        self.service.on_client_lost(adv.get_client(), on_client_lost)
        adv.on_client_lost = on_client_lost

        await self.ActiveInstances.set_async(len(self.advertisements))
        await self.SupportedInstances.set_async(self.__supported_instances)

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def UnregisterAdvertisement(self, path: str) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to unregister advertisement {path}")
        if adv := self.advertisements.get((sender, path)):
            await self.__del_advertisement(adv)
            return
        raise DBusBluezDoesNotExistError("Does Not Exist")

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def ActiveInstances(self) -> int:
        return len(self.advertisements)

    @ActiveInstances.setter_private
    def ActiveInstances_setter(self, value: int) -> None:
        pass

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def SupportedInstances(self) -> int:
        return self.__supported_instances

    @SupportedInstances.setter_private
    def SupportedInstances_setter(self, value: int) -> None:
        pass

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def SupportedIncludes(self) -> list[str]:
        return ["tx-power", "appearance", "local-name"]

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def SupportedSecondaryChannels(self) -> list[str]:
        return ["1M"]

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def SupportedCapabilities(self) -> dict[str, tuple[str, Any]]:
        caps = {}
        caps["MaxAdvLen"] = ("y", 31)
        caps["MaxScanRespLen"] = ("y", 31)
        return caps

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def SupportedFeatures(self) -> list[str]:
        return []
