# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import asyncio
import logging
import os
from typing import Any

import sdbus

from ..interfaces.GattCharacteristic import GattCharacteristicInterface
from ..utils import (BluetoothUUID, DBusClientMixin, dbus_method_async_except_logging,
                     dbus_property_async_except_logging)


class GattCharacteristicClient(DBusClientMixin, GattCharacteristicInterface):
    """D-Bus client for GATT characteristic."""

    def __init__(self, service, path):
        super().__init__(service, path)


class GattCharacteristicClientLink(GattCharacteristicInterface):
    """GATT characteristic server linked with a remote client."""

    def __init__(self, client: GattCharacteristicClient, service):
        super().__init__()
        self.client = client
        self.service = service

        self.f_read = None
        self.f_write = None
        self.mtu = self.client.MTU.get(512)

    def __str__(self):
        return self.client.get_object_path()

    def get_object_path(self):
        handle = hex(self.client.Handle.get())[2:].zfill(4)
        return f"{self.service.get_object_path()}/char{handle}"

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def ReadValue(self, options: dict[str, tuple[str, Any]]) -> bytes:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to read value of {self}")
        return await self.client.ReadValue(options)

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def WriteValue(self, value: bytes, options: dict[str, tuple[str, Any]]) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to write value of {self}")
        if self.client.WriteAcquired.get() is None:
            await self.client.WriteValue(value, options)
        elif self.client.WriteAcquired.get() is False:
            fd, self.mtu = await self.client.AcquireWrite({
                "device": ("o", self.service.device.get_object_path()),
                "mtu": ("q", self.mtu),
                "link": ("s", "LE")})
            self.f_write = open(os.dup(fd), "wb", buffering=0)
        self.f_write.write(value)

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def AcquireWrite(self, options: dict[str, tuple[str, Any]]) -> tuple[int, int]:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to acquire write of {self}")
        return await self.client.AcquireWrite(options)

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def AcquireNotify(self, options: dict[str, tuple[str, Any]]) -> tuple[int, int]:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to acquire notify of {self}")
        return await self.client.AcquireNotify(options)

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def StartNotify(self) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to start notification of {self}")
        if self.client.NotifyAcquired.get() is None:
            await self.client.StartNotify()
        elif self.client.NotifyAcquired.get() is False:
            fd, self.mtu = await self.client.AcquireNotify({
                "device": ("o", self.service.device.get_object_path()),
                "mtu": ("q", self.mtu),
                "link": ("s", "LE")})
            # Duplicate the file descriptor before opening the socket to
            # avoid closing the file descriptor by the D-Bus library.
            self.f_read = open(os.dup(fd), "rb", buffering=0)

            def reader():
                if data := self.f_read.read(self.mtu):
                    asyncio.create_task(self.Value.set_async(data))
                    asyncio.create_task(self.client.Confirm())
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
        logging.debug(f"Client {sender} requested to stop notification of {self}")
        if self.client.NotifyAcquired.get() is None:
            await self.client.StopNotify()
        elif self.client.NotifyAcquired.get() is True:
            if self.f_read is not None:
                loop = asyncio.get_running_loop()
                loop.remove_reader(self.f_read.fileno())
                self.f_read.close()
                self.f_read = None

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def Confirm(self) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} confirmed {self}")
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
