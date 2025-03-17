# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import sdbus

from ..interfaces.GattService import GattServiceInterface
from ..utils import BluetoothUUID, DBusClientMixin, dbus_property_async_except_logging


class GattServiceClient(DBusClientMixin, GattServiceInterface):
    """D-Bus client for GATT service."""

    def __init__(self, service, path):
        super().__init__(service, path)


class GattServiceClientLink(GattServiceInterface):
    """GATT service server linked with a remote client."""

    def __init__(self, client: GattServiceClient, device):
        super().__init__()
        self.client = client
        self.device = device

    def get_object_path(self):
        handle = hex(self.client.Handle.get())[2:].zfill(4)
        return f"{self.device.get_object_path()}/service{handle}"

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def UUID(self) -> str:
        return BluetoothUUID(self.client.UUID.get())

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Primary(self) -> bool:
        return self.client.Primary.get()

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Device(self) -> str:
        return self.device.get_object_path()

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Includes(self) -> list[str]:
        return self.client.Includes.get([])

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Handle(self) -> int:
        return self.client.Handle.get()
