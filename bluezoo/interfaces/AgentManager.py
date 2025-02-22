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

    def __init__(self, controller):
        self.controller = controller
        super().__init__()

    @dbus_method_async(
        input_signature="os",
        input_args_names=("agent", "capability"))
    async def RegisterAgent(self, agent: str, capability: str) -> None:
        sender = sdbus.get_current_message().sender
        capability = capability or "KeyboardDisplay"  # Fallback to default capability.
        logging.debug(f"Client {sender} requested to register agent {agent}")
        self.controller.register_agent(
            Agent(capability, sender, agent, self.controller.service.bus))

    @dbus_method_async(
        input_signature="o",
        input_args_names=("agent",))
    async def UnregisterAgent(self, agent: str) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to unregister agent {agent}")
        for agent_ in self.controller.agents[:]:
            if agent_.destination == (sender, agent):
                self.controller.unregister_agent(agent_)

    @dbus_method_async(
        input_signature="o",
        input_args_names=("agent",))
    async def RequestDefaultAgent(self, agent: str) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to set {agent} as default agent")
        for agent_ in self.controller.agents:
            if agent_.destination == (sender, agent):
                self.controller.set_default_agent(agent_)
