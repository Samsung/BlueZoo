# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import sdbus

from .exceptions import DBusBluezAlreadyExistsError, DBusBluezDoesNotExistError
from .interfaces.Agent import AgentInterface
from .interfaces.AgentManager import AgentManagerInterface
from .log import logger
from .utils import DBusClientMixin, create_background_task, dbus_method_async_except_logging


class AgentClient(DBusClientMixin, AgentInterface):
    """D-Bus client for the Agent interface."""

    def __init__(self, service, path, capability: str, service_lost_callback):
        super().__init__(service, path, service_lost_callback)
        self.capability = capability

    def __str__(self):
        return f"agent[{self.capability}]"


class RootManager(AgentManagerInterface):

    def __init__(self, mock):
        super().__init__()
        self.mock = mock

        # Default agent.
        self.agent = None
        # Agents registered by the clients.
        self.agents: dict[str, AgentClient] = {}

    def get_object_path(self):
        return "/org/bluez"

    async def __del_agent(self, agent: AgentClient):
        logger.info("Unregistering %s", agent)

        if agent == self.agent:
            self.agent = None

        self.agents.pop(agent.get_client())
        await agent.cleanup()

        if self.agents:
            # Promote the lastly registered agent to be the default one.
            self.agent = list(self.agents.values())[-1]

        if self.agent is None:
            # If there are no agents, the adapters cannot be pairable.
            for adapter in self.mock.adapters.values():
                create_background_task(adapter.Pairable.set_async(False))

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def RegisterAgent(self, path: str, capability: str) -> None:
        sender = sdbus.get_current_message().sender
        logger.debug("Client %s requested to register agent %s", sender, path)
        assert sender is not None, "D-Bus message sender is None"
        capability = capability or "KeyboardDisplay"  # Fallback to default capability.

        # Do not allow registering more than one agent per client.
        if sender in self.agents:
            msg = "Already Exists"
            raise DBusBluezAlreadyExistsError(msg)

        async def on_sender_lost():
            await self.__del_agent(agent)

        agent = AgentClient(sender, path, capability, on_sender_lost)
        logger.info("Registering %s", agent)

        if self.agent is None:
            logger.info("Setting %s as default agent", agent)
            self.agent = agent
        self.agents[sender] = agent

        # If there is at least one agent, the adapters are pairable.
        for adapter in self.mock.adapters.values():
            if not adapter.pairable:
                create_background_task(adapter.Pairable.set_async(True))

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def UnregisterAgent(self, path: str) -> None:
        sender = sdbus.get_current_message().sender
        logger.debug("Client %s requested to unregister agent %s", sender, path)
        assert sender is not None, "D-Bus message sender is None"
        if (agent := self.agents.get(sender)) and agent.get_object_path() == path:
            await self.__del_agent(agent)
            return
        msg = "Does Not Exist"
        raise DBusBluezDoesNotExistError(msg)

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def RequestDefaultAgent(self, path: str) -> None:
        sender = sdbus.get_current_message().sender
        logger.debug("Client %s requested to set %s as default agent", sender, path)
        assert sender is not None, "D-Bus message sender is None"
        if (agent := self.agents.get(sender)) and agent.get_object_path() == path:
            logger.info("Setting %s as default agent", agent)
            self.agent = agent
            return
        msg = "Does Not Exist"
        raise DBusBluezDoesNotExistError(msg)
