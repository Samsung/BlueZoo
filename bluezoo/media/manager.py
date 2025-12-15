# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

from typing import Any

import sdbus

from ..exceptions import DBusBluezDoesNotExistError
from ..interfaces.Media import MediaInterface
from ..log import logger
from ..utils import (BluetoothUUID, dbus_method_async_except_logging,
                     dbus_property_async_except_logging)
from .endpoint import MediaEndpointClient


class MediaManager(MediaInterface):
    """Media manager."""

    def __init__(self):
        super().__init__()
        # Keep track of registered media endpoints and applications.
        self.endpoints: dict[tuple[str, str], Any] = {}
        self.apps: dict[tuple[str, str], Any] = {}

    async def cleanup(self):
        pass

    async def __del_endpoint(self, endpoint):
        logger.info("Removing %s", endpoint)
        self.endpoints.pop((endpoint.get_client(), endpoint.get_object_path()))
        await endpoint.cleanup()

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def RegisterEndpoint(self, path: str,
                               properties: dict[str, tuple[str, Any]]) -> None:
        sender = sdbus.get_current_message().sender
        logger.debug("Client %s requested to register media endpoint %s", sender, path)
        assert sender is not None, "D-Bus message sender is None"

        async def on_sender_lost():
            await self.__del_endpoint(endpoint)

        endpoint = MediaEndpointClient(sender, path, properties, on_sender_lost)
        await endpoint.properties_setup_sync_task()

        logger.info("Registering %s", endpoint)
        self.endpoints[sender, path] = endpoint

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def UnregisterEndpoint(self, path: str) -> None:
        sender = sdbus.get_current_message().sender
        logger.debug("Client %s requested to unregister media endpoint %s", sender, path)
        assert sender is not None, "D-Bus message sender is None"
        if endpoint := self.endpoints.get((sender, path)):
            await self.__del_endpoint(endpoint)
            return
        msg = "Does Not Exist"
        raise DBusBluezDoesNotExistError(msg)

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def RegisterApplication(self, path: str,
                                  options: dict[str, tuple[str, Any]]) -> None:
        sender = sdbus.get_current_message().sender
        logger.debug("Client %s requested to register media application %s", sender, path)
        assert sender is not None, "D-Bus message sender is None"

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def UnregisterApplication(self, path: str) -> None:
        sender = sdbus.get_current_message().sender
        logger.debug("Client %s requested to unregister media application %s", sender, path)
        assert sender is not None, "D-Bus message sender is None"

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def SupportedUUIDs(self) -> list[str]:
        return [BluetoothUUID("0000110a"), BluetoothUUID("0000110b")]

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def SupportedFeatures(self) -> list[str]:
        return []
