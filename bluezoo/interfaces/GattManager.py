# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import logging
from typing import Any

import sdbus

from ..gatt import (GattApplication, GattCharacteristicClient, GattDescriptorClient,
                    GattServiceClient)
from ..utils import dbus_method_async, dbus_method_async_except_logging


class GattManagerInterface(sdbus.DbusInterfaceCommonAsync,
                           interface_name="org.bluez.GattManager1"):

    async def add_gatt_application(self, app: GattApplication) -> None:
        raise NotImplementedError

    async def del_gatt_application(self, app: GattApplication) -> None:
        raise NotImplementedError

    def get_gatt_application(self, client, path) -> GattApplication:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="oa{sv}",
        input_args_names=("application", "options"))
    @dbus_method_async_except_logging
    async def RegisterApplication(self, application: str,
                                  options: dict[str, tuple[str, Any]]) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to register GATT application {application}")
        app = GattApplication(sender, application, options)
        await app.object_manager_setup_sync_task(
            (GattServiceClient, GattCharacteristicClient, GattDescriptorClient))
        await self.add_gatt_application(app)

    @dbus_method_async(
        input_signature="o",
        input_args_names=("application",))
    @dbus_method_async_except_logging
    async def UnregisterApplication(self, application: str) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to unregister GATT application {application}")
        await self.del_gatt_application(self.get_gatt_application(sender, application))
