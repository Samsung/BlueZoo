# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import logging

import sdbus

from ..helpers import dbus_method_async
from .Agent import AgentInterface


class Agent(AgentInterface):
    """D-Bus client for the Agent interface."""

    def __init__(self, capability: str, client, path, bus):
        super().__init__()
        self.capability = capability
        self.destination = (client, path)
        self._connect(client, path, bus)


class AgentManagerInterface(sdbus.DbusInterfaceCommonAsync,
                            interface_name="org.bluez.AgentManager1"):

    def __init__(self, service):
        super().__init__()
        self.service = service
        self.default = None
        self.agents = []

    @dbus_method_async(
        input_signature="os",
        input_args_names=("agent", "capability"))
    async def RegisterAgent(self, agent: str, capability: str) -> None:
        sender = sdbus.get_current_message().sender
        capability = capability or "KeyboardDisplay"  # Fallback to default capability.
        logging.debug(f"Client {sender} requested to register agent {agent}")
        logging.info(f"Registering agent with {capability} capability")
        self.agents.append(Agent(capability, sender, agent, self.service.bus))

    @dbus_method_async(
        input_signature="o",
        input_args_names=("agent",))
    async def UnregisterAgent(self, agent: str) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to unregister agent {agent}")
        for agent in self.agents[:]:
            if agent.destination == (sender, agent):
                logging.info(f"Unregistering agent with {agent.capability} capability")
                self.agents.remove(agent)

    @dbus_method_async(
        input_signature="o",
        input_args_names=("agent",))
    async def RequestDefaultAgent(self, agent: str) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to set {agent} as default agent")
        for agent in self.agents:
            if agent.destination == (sender, agent):
                logging.info(f"Setting default agent with {agent.capability} capability")
                self.default = agent
