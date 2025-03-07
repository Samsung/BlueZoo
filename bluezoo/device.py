# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import asyncio
import logging

from .interfaces import DeviceInterface
from .utils import NoneTask


class Device(DeviceInterface):
    """Local adapter's view on a peer adapter."""

    PAIRING_TIMEOUT = 60
    CONNECTING_TIMEOUT = 60

    def __init__(self, peer_adapter, **kwargs):
        super().__init__()
        # The adapter that manages this device.
        self.peer_adapter = peer_adapter

        # The adapter to which this device is added.
        self.adapter = None
        # The device representing local adapter on the peer adapter.
        self.peer_device: Device = None

        self.is_le = False
        self.is_br_edr = False

        self.address = peer_adapter.address
        self.name_ = peer_adapter.name
        self.class_ = peer_adapter.class_
        self.appearance = 0
        self.paired = False
        self.pairing_task = NoneTask()
        self.bonded = False
        self.trusted = False
        self.blocked = False
        self.connected = False
        self.connecting_task = NoneTask()
        self.services_resolved = False
        self.service_data = {}
        self.uuids = []

        # Set the properties from the keyword arguments.
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return f"device[{self.address}]"

    def setup_adapter(self, adapter):
        """Set the adapter to which this device is added."""
        self.peer_device = Device(adapter)
        self.adapter = adapter

    def get_object_path(self):
        return "/".join((
            self.adapter.get_object_path(),
            f"dev_{self.address.replace(':', '_')}"))

    @property
    def name(self):
        return getattr(self, "name__", self.name_)

    @name.setter
    def name_setter(self, value):
        self.name__ = value

    async def properties_sync(self, device):
        """Synchronize the properties with another device."""
        if self.name_ != device.name:
            await self.Name.set_async(device.name)
        if self.appearance != device.appearance:
            await self.Appearance.set_async(device.appearance)
        if self.uuids != device.uuids:
            await self.ServiceUUIDs.set_async(device.uuids)
        if self.service_data != device.service_data:
            await self.ServiceData.set_async(device.service)

    async def connect(self, uuid: str = None) -> None:

        async def task():
            # Use the peer's adapter to connect with this device.
            logging.info(f"Connecting {self} with {self.adapter}")
            # Check if the peer adapter is trusted on the device's adapter.
            if not self.peer_device.trusted:
                await self.adapter.controller.agent.RequestAuthorization(self.get_object_path())
            # Mark devices as connected.
            await self.peer_device.Connected.set_async(True)
            await self.Connected.set_async(True)

        if not self.paired:
            await self.pair()

        try:
            self.connecting_task = asyncio.create_task(task())
            async with asyncio.timeout(self.CONNECTING_TIMEOUT):
                await self.connecting_task
        except asyncio.TimeoutError:
            logging.info(f"Connecting with {self} timed out")

    async def disconnect(self, uuid: str = None) -> None:
        self.connecting_task.cancel()
        logging.info(f"Disconnecting {self}")
        await self.peer_device.Connected.set_async(False)
        await self.Connected.set_async(False)

    async def pair(self) -> None:

        async def task():
            # Use the peer's adapter to pair with this device.
            logging.info(f"Pairing {self} with {self.adapter}")
            if self.adapter.controller.agent.capability == "NoInputNoOutput":
                # There is no user interface to confirm the pairing.
                pass
            else:
                raise NotImplementedError
            # Add paired peer device to our adapter.
            self.peer_device.paired = True
            self.peer_device.bonded = True
            await self.peer_adapter.add_device(self.peer_device)
            # Mark the device as paired and bonded.
            await self.Paired.set_async(True)
            await self.Bonded.set_async(True)

        try:
            self.pairing_task = asyncio.create_task(task())
            async with asyncio.timeout(self.PAIRING_TIMEOUT):
                await self.pairing_task
        except asyncio.TimeoutError:
            logging.info(f"Pairing with {self} timed out")

    async def cancel_pairing(self) -> None:
        if not self.pairing_task.done():
            logging.info(f"Canceling pairing with {self}")
        self.pairing_task.cancel()
