# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import logging

import sdbus

from ..helpers import dbus_method_async
from .Agent import AgentInterface


class Agent(AgentInterface):
    """D-Bus client for the Agent interface."""

    def __init__(self, capability: str, client, path):
        super().__init__()
        self.capability = capability
        self._destination = (client, path)
        self._connect(client, path)


class AgentManagerInterface(sdbus.DbusInterfaceCommonAsync,
                            interface_name="org.bluez.AgentManager1"):

    agents: list[Agent] = None

    def register_agent(self, agent: Agent) -> None:
        raise NotImplementedError

    def unregister_agent(self, agent: Agent) -> None:
        raise NotImplementedError

    def set_default_agent(self, agent: Agent) -> None:
        raise NotImplementedError

    def get_agent(self, client, path):
        for agent in self.agents:
            if agent._destination == (client, path):
                return agent
        return None

    @dbus_method_async(
        input_signature="os",
        input_args_names=("agent", "capability"))
    async def RegisterAgent(self, agent: str, capability: str) -> None:
        sender = sdbus.get_current_message().sender
        capability = capability or "KeyboardDisplay"  # Fallback to default capability.
        logging.debug(f"Client {sender} requested to register agent {agent}")
        self.register_agent(Agent(capability, sender, agent))

    @dbus_method_async(
        input_signature="o",
        input_args_names=("agent",))
    async def UnregisterAgent(self, agent: str) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to unregister agent {agent}")
        if agent_ := self.get_agent(sender, agent):
            self.unregister_agent(agent_)

    @dbus_method_async(
        input_signature="o",
        input_args_names=("agent",))
    async def RequestDefaultAgent(self, agent: str) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to set {agent} as default agent")
        if agent_ := self.get_agent(sender, agent):
            self.set_default_agent(agent_)
