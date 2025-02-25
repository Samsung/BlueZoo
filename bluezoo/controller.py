# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import asyncio
import logging
from typing import Optional

from .interfaces import AgentManagerInterface
from .interfaces.AgentManager import Agent


class Controller(AgentManagerInterface):

    def __init__(self, service):
        self.service = service
        super().__init__()

        self.agent = None
        self.agents = []

    def get_object_path(self):
        return "/org/bluez"

    async def add_agent(self, agent):
        logging.info(f"Adding agent with {agent.capability} capability")

        if self.agent is None:
            self.agent = agent
        self.agents.append(agent)

        async def wait_for_client_lost():
            client, path = agent.get_client()
            await self.service.wait_for_client_lost(client)
            logging.debug(f"Client {client} lost, removing agent {path}")
            await self.del_agent(agent)
        agent.client_lost_task = asyncio.create_task(wait_for_client_lost())

        # If there is at least one agent, the adapters are pairable.
        for adapter in self.service.adapters.values():
            if not adapter.pairable:
                asyncio.create_task(adapter.Pairable.set_async(True))

    async def del_agent(self, agent):
        logging.info(f"Removing agent with {agent.capability} capability")

        if agent == self.agent:
            self.agent = None
        agent.client_lost_task.cancel()
        self.agents.remove(agent)

        if self.agents:
            # Promote the lastly registered agent to be the default one.
            self.agent = self.agents[-1]

        if self.agent is None:
            # If there are no agents, the adapters cannot be pairable.
            for adapter in self.service.adapters.values():
                asyncio.create_task(adapter.Pairable.set_async(False))

    def get_agent(self, client, path) -> Optional[Agent]:
        for agent in self.agents:
            if agent.get_client() == (client, path):
                return agent
        return None

    async def set_default_agent(self, agent):
        logging.info(f"Setting default agent with {agent.capability} capability")
        self.agent = agent
