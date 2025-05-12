# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import asyncio
import logging

import sdbus

from .exceptions import DBusBluezAlreadyExistsError, DBusBluezDoesNotExistError
from .interfaces.Agent import AgentInterface
from .interfaces.AgentManager import AgentManagerInterface
from .utils import DBusClientMixin, dbus_method_async_except_logging


class AgentClient(DBusClientMixin, AgentInterface):
    """D-Bus client for the Agent interface."""

    def __init__(self, service, path, capability: str):
        super().__init__(service, path)
        self.capability = capability

    def __str__(self):
        return f"agent[{self.capability}]"


class Controller(AgentManagerInterface):

    def __init__(self, service):
        self.service = service
        super().__init__()

        # Default agent.
        self.agent = None
        # Agents registered by the clients.
        self.agents = {}

    def get_object_path(self):
        return "/org/bluez"

    async def __del_agent(self, agent: AgentClient):
        logging.info(f"Unregistering {agent}")

        if agent == self.agent:
            self.agent = None
        self.service.on_client_lost_remove(agent.get_client(), agent.on_client_lost)
        self.agents.pop(agent.get_client())

        if self.agents:
            # Promote the lastly registered agent to be the default one.
            self.agent = list(self.agent.values())[-1]

        if self.agent is None:
            # If there are no agents, the adapters cannot be pairable.
            for adapter in self.service.adapters.values():
                asyncio.create_task(adapter.Pairable.set_async(False))

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def RegisterAgent(self, path: str, capability: str) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to register agent {path}")
        capability = capability or "KeyboardDisplay"  # Fallback to default capability.

        # Do not allow registering more than one agent per client.
        for sender in self.agents:
            raise DBusBluezAlreadyExistsError("Already Exists")

        agent = AgentClient(sender, path, capability)
        logging.info(f"Registering {agent}")

        if self.agent is None:
            logging.info(f"Setting {agent} as default agent")
            self.agent = agent
        self.agents[sender] = agent

        async def on_client_lost():
            await self.__del_agent(agent)
        self.service.on_client_lost(sender, on_client_lost)
        agent.on_client_lost = on_client_lost

        # If there is at least one agent, the adapters are pairable.
        for adapter in self.service.adapters.values():
            if not adapter.pairable:
                asyncio.create_task(adapter.Pairable.set_async(True))

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def UnregisterAgent(self, path: str) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to unregister agent {path}")
        if agent := self.agents.get(sender):
            if agent.get_object_path() == path:
                await self.__del_agent(agent)
                return
        raise DBusBluezDoesNotExistError("Does Not Exist")

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def RequestDefaultAgent(self, path: str) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to set {path} as default agent")
        if agent := self.agents.get(sender):
            if agent.get_object_path() == path:
                logging.info(f"Setting {agent} as default agent")
                self.agent = agent
                return
        raise DBusBluezDoesNotExistError("Does Not Exist")
