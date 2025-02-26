# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import logging
from typing import Optional

import sdbus

from ..helpers import dbus_method_async, DBusClientMixin
from .Agent import AgentInterface


class Agent(DBusClientMixin, AgentInterface):
    """D-Bus client for the Agent interface."""

    def __init__(self, service, path, capability: str):
        super().__init__(service, path)
        self.capability = capability


class AgentManagerInterface(sdbus.DbusInterfaceCommonAsync,
                            interface_name="org.bluez.AgentManager1"):

    async def add_agent(self, agent: Agent) -> None:
        raise NotImplementedError

    async def del_agent(self, agent: Agent) -> None:
        raise NotImplementedError

    def get_agent(self, client, path) -> Optional[Agent]:
        raise NotImplementedError

    async def set_default_agent(self, agent: Agent) -> None:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="os",
        input_args_names=("agent", "capability"))
    async def RegisterAgent(self, agent: str, capability: str) -> None:
        sender = sdbus.get_current_message().sender
        capability = capability or "KeyboardDisplay"  # Fallback to default capability.
        logging.debug(f"Client {sender} requested to register agent {agent}")
        await self.add_agent(Agent(sender, agent, capability))

    @dbus_method_async(
        input_signature="o",
        input_args_names=("agent",))
    async def UnregisterAgent(self, agent: str) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to unregister agent {agent}")
        if agent_ := self.get_agent(sender, agent):
            await self.del_agent(agent_)

    @dbus_method_async(
        input_signature="o",
        input_args_names=("agent",))
    async def RequestDefaultAgent(self, agent: str) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to set {agent} as default agent")
        if agent_ := self.get_agent(sender, agent):
            await self.set_default_agent(agent_)
