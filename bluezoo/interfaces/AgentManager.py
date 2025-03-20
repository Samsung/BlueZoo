# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import sdbus

from ..utils import dbus_method_async


class AgentManagerInterface(sdbus.DbusInterfaceCommonAsync,
                            interface_name="org.bluez.AgentManager1"):

    @dbus_method_async(
        input_signature="os",
        input_args_names=("agent", "capability"))
    async def RegisterAgent(self, agent: str, capability: str) -> None:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="o",
        input_args_names=("agent",))
    async def UnregisterAgent(self, agent: str) -> None:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="o",
        input_args_names=("agent",))
    async def RequestDefaultAgent(self, agent: str) -> None:
        raise NotImplementedError
