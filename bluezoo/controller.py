# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import asyncio
import logging

from .interfaces import AgentManagerInterface


class Controller(AgentManagerInterface):

    def __init__(self, service):
        self.service = service
        super().__init__()

        self.agents = []
        self.agent_default = None

    def get_object_path(self):
        return "/org/bluez"

    def register_agent(self, agent):
        logging.info(f"Registering agent with {agent.capability} capability")

        if self.agent_default is None:
            self.agent_default = agent
        self.agents.append(agent)

        # If there is at least one agent, the adapters are pairable.
        for adapter in self.service.adapters.values():
            if not adapter.pairable:
                asyncio.create_task(adapter.Pairable.set_async(True))

    def unregister_agent(self, agent):
        logging.info(f"Unregistering agent with {agent.capability} capability")

        if agent == self.agent_default:
            self.agent_default = None
        self.agents.remove(agent)

        if self.agents:
            # Promote the lastly registered agent to be the default one.
            self.agent_default = self.agents[-1]

        if self.agent_default is None:
            # If there are no agents, the adapters cannot be pairable.
            for adapter in self.service.adapters.values():
                asyncio.create_task(adapter.Pairable.set_async(False))

    def set_default_agent(self, agent):
        logging.info(f"Setting default agent with {agent.capability} capability")
        self.agent_default = agent
