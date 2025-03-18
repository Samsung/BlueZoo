# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import logging
from typing import Any

import sdbus

from ..interfaces.GattDescriptor import GattDescriptorInterface
from ..utils import (BluetoothUUID, DBusClientMixin, dbus_method_async_except_logging,
                     dbus_property_async_except_logging)


class GattDescriptorClient(DBusClientMixin, GattDescriptorInterface):
    """D-Bus client for GATT descriptor."""

    def __init__(self, service, path):
        super().__init__(service, path)


class GattDescriptorClientLink(GattDescriptorInterface):
    """GATT descriptor server linked with a remote client."""

    def __init__(self, client: GattDescriptorClient, characteristic):
        super().__init__()
        self.client = client
        self.characteristic = characteristic

    def __str__(self):
        return self.get_object_path()

    def __prepare_options(self, options: dict):
        options.update({
            "device": ("o", self.characteristic.device_path),
            "mtu": ("q", self.characteristic.mtu),
            "link": ("s", self.characteristic.link)})
        return options

    def get_object_path(self):
        handle = hex(self.client.Handle.get())[2:].zfill(4)
        return f"{self.characteristic.get_object_path()}/desc{handle}"

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def ReadValue(self, options: dict[str, tuple[str, Any]]) -> bytes:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to read value of {self}")
        return await self.client.ReadValue(self.__prepare_options(options))

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def WriteValue(self, value: bytes, options: dict[str, tuple[str, Any]]) -> None:
        sender = sdbus.get_current_message().sender
        logging.debug(f"Client {sender} requested to write value of {self}")
        await self.client.WriteValue(value, self.__prepare_options(options))

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def UUID(self) -> str:
        return BluetoothUUID(self.client.UUID.get())

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Characteristic(self) -> str:
        return self.characteristic.get_object_path()

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Value(self) -> bytes:
        return self.client.Value.get(b"")

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Flags(self) -> list[str]:
        return self.client.Flags.get([])

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Handle(self) -> int:
        return self.client.Handle.get()
