# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

from typing import Any

import sdbus

from ..utils import dbus_method_async


class GattManagerInterface(sdbus.DbusInterfaceCommonAsync,
                           interface_name="org.bluez.GattManager1"):

    @dbus_method_async(
        input_signature="oa{sv}",
        input_args_names=("application", "options"))
    async def RegisterApplication(self, application: str,
                                  options: dict[str, tuple[str, Any]]) -> None:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="o",
        input_args_names=("application",))
    async def UnregisterApplication(self, application: str) -> None:
        raise NotImplementedError
