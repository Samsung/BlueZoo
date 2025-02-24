# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import asyncio
import logging

from .helpers import NoneTask
from .interfaces import DeviceInterface


class Device(DeviceInterface):

    PAIRING_TIMEOUT = 60
    CONNECTING_TIMEOUT = 60

    def __init__(self, adapter, **kwargs):
        super().__init__()

        # The adapter that manages this device.
        self.adapter = adapter
        # The peer adapter to which this device is added. It is set
        # when the device is added to a peer adapter.
        self.peer = None

        self.address = adapter.address
        self.name_ = adapter.name
        self.class_ = adapter.class_
        self.appearance = 0
        self.paired = False
        # The Device representing our adapter on the peer adapter.
        self.paired_device = None
        self.pairing_timeout_task = NoneTask()
        self.pairing_task = NoneTask()
        self.bonded = False
        self.trusted = False
        self.blocked = False
        self.connected = False
        self.connecting_timeout_task = NoneTask()
        self.connecting_task = NoneTask()
        self.services_resolved = False
        self.service_data = {}
        self.uuids = []

        # Set the properties from the keyword arguments.
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get_object_path(self):
        return "/".join((
            self.peer.get_object_path(),
            f"dev_{self.address.replace(':', '_')}"))

    @property
    def name(self):
        return getattr(self, "name__", self.name_)

    @name.setter
    def name_setter(self, value):
        self.name__ = value

    async def connect(self) -> None:

        async def task():
            # Use the peer's adapter to connect with this device.
            logging.info(f"Connecting device {self.address} with adapter {self.peer.id}")
            # Check if the peer adapter is trusted on the device's adapter.
            if not self.paired_device.trusted:
                await self.adapter.controller.agent.RequestAuthorization(self.get_object_path())
            # Cancel the timeout task.
            logging.debug(f"Canceling connecting timeout for device {self.address}")
            self.connecting_timeout_task.cancel()
            # Mark devices as connected.
            await self.paired_device.Connected.set_async(True)
            await self.Connected.set_async(True)

        async def task_timeout():
            logging.debug(f"Starting connecting timeout for device {self.address}")
            await asyncio.sleep(self.CONNECTING_TIMEOUT)
            logging.info(f"Connecting with device {self.address} timed out")
            self.connecting_task.cancel()

        if not self.paired:
            await self.pair()

        self.connecting_timeout_task = asyncio.create_task(task_timeout())
        self.connecting_task = asyncio.create_task(task())
        await self.connecting_task

    async def disconnect(self) -> None:
        self.connecting_task.cancel()
        self.connecting_timeout_task.cancel()
        logging.info(f"Disconnecting device {self.address}")
        await self.connected_device.Connected.set_async(False)
        await self.Connected.set_async(False)

    async def pair(self) -> None:

        async def task():
            # Use the peer's adapter to pair with this device.
            logging.info(f"Pairing device {self.address} with adapter {self.peer.id}")
            if self.adapter.controller.agent.capability == "NoInputNoOutput":
                # There is no user interface to confirm the pairing.
                pass
            else:
                raise NotImplementedError
            # Cancel the timeout task.
            logging.debug(f"Canceling pairing timeout for device {self.address}")
            self.pairing_timeout_task.cancel()
            # Add peer adapter as a paired device to the device's adapter.
            self.paired_device = Device(self.peer, paired=True, bonded=True)
            self.adapter.add_device(self.paired_device)
            # Mark the device as paired.
            await self.Paired.set_async(True)
            await self.Bonded.set_async(True)

        async def task_timeout():
            logging.debug(f"Starting pairing timeout for device {self.address}")
            await asyncio.sleep(self.PAIRING_TIMEOUT)
            logging.info(f"Pairing with device {self.address} timed out")
            self.pairing_task.cancel()

        self.pairing_timeout_task = asyncio.create_task(task_timeout())
        self.pairing_task = asyncio.create_task(task())
        await self.pairing_task

    async def cancel_pairing(self) -> None:
        if not self.pairing_task.done():
            logging.info(f"Canceling pairing with device {self.address}")
        self.pairing_task.cancel()
        self.pairing_timeout_task.cancel()
