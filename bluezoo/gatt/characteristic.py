# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import asyncio
import os
from typing import Any, BinaryIO

import sdbus

from .. import events
from ..interfaces.GattCharacteristic import GattCharacteristicInterface
from ..log import logger
from ..utils import (BluetoothUUID, DBusClientMixin, create_background_task,
                     dbus_method_async_except_logging, dbus_property_async_except_logging)
from .service import GattServiceClientLink


class GattCharacteristicClient(DBusClientMixin, GattCharacteristicInterface):
    """D-Bus client for GATT characteristic."""

    def __init__(self, service, path):
        super().__init__(service, path)


class GattCharacteristicClientLink(GattCharacteristicInterface):
    """GATT characteristic server linked with a remote client."""

    def __init__(self, client: GattCharacteristicClient, service: GattServiceClientLink):
        super().__init__()
        self.client = client
        self.service = service

        self.mtu = self.client.MTU.get(512)
        self.link = "LE"

        self.client_props_changed_subscription = events.Subscription()
        self.f_read: BinaryIO | None = None
        self.f_write: BinaryIO | None = None

    def __str__(self):
        return self.client.get_object_path()

    def __prepare_options(self, options: dict):
        options.update({
            "device": ("o", self.service.device.peer.get_object_path()),
            "mtu": ("q", self.mtu),
            "link": ("s", self.link)})
        return options

    def get_object_path(self):
        handle = hex(self.client.Handle.get())[2:].zfill(4)
        return f"{self.service.get_object_path()}/char{handle}"

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def ReadValue(self, options: dict[str, tuple[str, Any]]) -> bytes:
        sender = sdbus.get_current_message().sender
        logger.debug("Client %s requested to read value of %s", sender, self)
        return await self.client.ReadValue(self.__prepare_options(options))

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def WriteValue(self, value: bytes, options: dict[str, tuple[str, Any]]) -> None:
        sender = sdbus.get_current_message().sender
        acquired = self.client.WriteAcquired.get()
        logger.debug("Client %s requested to write value of %s", sender, self)
        if acquired is None:
            await self.client.WriteValue(value, self.__prepare_options(options))
        elif not acquired:
            fd, self.mtu = await self.client.AcquireWrite(self.__prepare_options({}))
            # Duplicate the file descriptor before opening the socket to
            # avoid closing the file descriptor by the D-Bus library.
            self.f_write = open(os.dup(fd), "wb", buffering=0)  # noqa: ASYNC230, SIM115
            self.f_write.write(value)
        elif self.f_write is not None:
            # Write to the previously acquired file descriptor.
            self.f_write.write(value)

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def AcquireWrite(self, options: dict[str, tuple[str, Any]]) -> tuple[int, int]:
        sender = sdbus.get_current_message().sender
        logger.debug("Client %s requested to acquire write of %s", sender, self)
        return await self.client.AcquireWrite(options)

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def AcquireNotify(self, options: dict[str, tuple[str, Any]]) -> tuple[int, int]:
        sender = sdbus.get_current_message().sender
        logger.debug("Client %s requested to acquire notify of %s", sender, self)
        return await self.client.AcquireNotify(options)

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def StartNotify(self) -> None:
        sender = sdbus.get_current_message().sender
        acquired = self.client.NotifyAcquired.get()
        logger.debug("Client %s requested to start notification of %s", sender, self)

        if acquired is None and not self.client.Notifying.get():

            async def on_properties_changed(properties: dict[str, Any]):
                if "Value" in properties:
                    await self.Value.set_async(properties["Value"])
                    # Confirm the indication via D-Bus call.
                    await self.client.Confirm()

            self.client_props_changed_subscription = events.subscribe(
                f"properties:changed:{id(self.client)}", on_properties_changed)
            await self.client.StartNotify()

        elif not acquired:
            fd, self.mtu = await self.client.AcquireNotify(self.__prepare_options({}))
            # Duplicate the file descriptor before opening the socket to
            # avoid closing the file descriptor by the D-Bus library.
            self.f_read = open(os.dup(fd), "r+b", buffering=0)  # noqa: ASYNC230, SIM115

            def reader():
                if data := self.f_read.read(self.mtu):
                    create_background_task(self.Value.set_async(data))
                    if "indicate" in self.client.Flags.get():
                        # Confirm the indication via file descriptor.
                        self.f_read.write(b"\x01")
                elif self.f_read is not None:
                    loop = asyncio.get_running_loop()
                    loop.remove_reader(self.f_read)
                    self.f_read.close()
                    self.f_read = None

            loop = asyncio.get_running_loop()
            loop.add_reader(self.f_read, reader)

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def StopNotify(self) -> None:
        sender = sdbus.get_current_message().sender
        acquired = self.client.NotifyAcquired.get()
        logger.debug("Client %s requested to stop notification of %s", sender, self)
        if acquired is None:
            await self.client.StopNotify()
            self.client_props_changed_subscription.unsubscribe()
        elif acquired:
            if self.f_read is not None:
                loop = asyncio.get_running_loop()
                loop.remove_reader(self.f_read.fileno())
                self.f_read.close()
                self.f_read = None

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def Confirm(self) -> None:
        sender = sdbus.get_current_message().sender
        logger.debug("Client %s confirmed %s", sender, self)
        return await self.client.Confirm()

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def UUID(self) -> str:
        return BluetoothUUID(self.client.UUID.get())

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Service(self) -> str:
        return self.service.get_object_path()

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Value(self) -> bytes:
        return self.client.Value.get(b"")

    @Value.setter_private
    def Value_setter(self, value: bytes):
        self.client.Value.cache(value)

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Notifying(self) -> bool:
        return self.client.Notifying.get(False)

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Flags(self) -> list[str]:
        return self.client.Flags.get([])

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def WriteAcquired(self) -> bool:
        return self.client.WriteAcquired.get(False)

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def NotifyAcquired(self) -> bool:
        return self.client.NotifyAcquired.get(False)

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def MTU(self) -> int:
        return self.mtu

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Handle(self) -> int:
        return self.client.Handle.get()
