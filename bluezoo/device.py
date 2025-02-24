# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import asyncio
import logging

from .interfaces import DeviceInterface


class Device(DeviceInterface):

    def __init__(self, adapter, **kwargs):
        super().__init__()

        # The adapter that manages this device.
        self.adapter = adapter
        # The peer adapter to which this device is connected. It is set
        # when the device is connected to a peer adapter.
        self.peer = None

        self.address = adapter.address
        self.name_ = adapter.name
        self.class_ = adapter.class_
        self.appearance = 0
        self.paired = False
        self.pairing_task = None
        self.bonded = False
        self.trusted = False
        self.blocked = False
        self.connected = False
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

    async def pair(self) -> None:
        async def task():
            # Use the peer's adapter to pair with this device.
            logging.info(f"Pairing device {self.address} with adapter {self.peer.id}")
            if self.adapter.controller.agent.capability == "NoInputNoOutput":
                # There is no user interface to confirm the pairing.
                pass
            else:
                raise NotImplementedError
            # Add peer adapter as a paired device to the device's adapter.
            self.adapter.add_device(Device(self.peer, paired=True, bonded=True))
            # Mark the device as paired.
            await self.Paired.set_async(True)
            await self.Bonded.set_async(True)
        self.pairing_task = asyncio.create_task(task())

    async def cancel_pairing(self) -> None:
        if self.pairing_task is not None:
            logging.info(f"Canceling pairing with device {self.address}")
            self.pairing_task.cancel()
