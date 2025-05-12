# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import asyncio
import logging
from typing import Any, Optional

import sdbus

from .gatt import (GattCharacteristicClient, GattCharacteristicClientLink, GattDescriptorClient,
                   GattDescriptorClientLink, GattServiceClient, GattServiceClientLink)
from .interfaces.Device import DeviceInterface
from .utils import NoneTask, dbus_method_async_except_logging, dbus_property_async_except_logging


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
        self.bearer = "last-seen"

        self.address = peer_adapter.address
        self.name_ = peer_adapter.name
        self.class_ = peer_adapter.class_
        self.icon = peer_adapter.class_.icon
        self.appearance = 0
        self.paired = False
        self.pairing_task = NoneTask()
        self.bonded = False
        self.trusted = False
        self.blocked = False
        self.wake_allowed = False
        self.connected = False
        self.connecting_task = NoneTask()
        self.services = {}
        self.services_resolved = False
        self.manufacturer_data = {}
        self.service_data = {}
        self.advertising_flags = b""
        self.advertising_data = {}
        self.uuids = []

        self.tx_power = None
        self.rssi = 0

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
    def name(self, value):
        self.name__ = value

    async def properties_sync(self, device):
        """Synchronize the properties with another device."""
        if self.name_ != device.name:
            await self.Name.set_async(device.name)
        if self.appearance != device.appearance:
            await self.Appearance.set_async(device.appearance)
        if self.uuids != device.uuids:
            await self.ServiceUUIDs.set_async(device.uuids)
        if self.manufacturer_data != device.manufacturer_data:
            await self.ManufacturerData.set_async(device.manufacturer_data)
        if self.service_data != device.service_data:
            await self.ServiceData.set_async(device.service)

    def connect_check_pairing_required(self, uuid):
        return self.is_br_edr and not self.paired

    def connect_check_authorization_required(self, uuid):
        # The connection is requested from our side, so we need to check if
        # our adapter is trusted on the peer adapter.
        return self.is_br_edr and not self.peer_device.trusted

    async def connect(self, uuid: Optional[str] = None) -> None:

        async def task():
            # Use the peer's adapter to connect with this device.
            logging.info(f"Connecting {self} with {self.adapter}")

            if self.connect_check_authorization_required(uuid):
                await self.peer_adapter.controller.agent.RequestAuthorization(self.get_object_path())

            # Mark devices as connected.
            await self.peer_device.Connected.set_async(True)
            await self.Connected.set_async(True)

            # Resolve LE services on the device.
            for app in self.peer_adapter.gatt_apps.values():
                links = {}
                for obj_path, obj in sorted(app.objects.items(), key=lambda x: x[0]):
                    if isinstance(obj, GattServiceClient):
                        link = GattServiceClientLink(obj, self)
                    if isinstance(obj, GattCharacteristicClient):
                        link = GattCharacteristicClientLink(obj, links[obj.Service.get()])
                    if isinstance(obj, GattDescriptorClient):
                        link = GattDescriptorClientLink(obj, links[obj.Characteristic.get()])
                    # Export the link with the manager.
                    self.peer_adapter.controller.service.manager.export_with_manager(
                        link.get_object_path(), link)
                    self.services[link.get_object_path()] = link
                    links[obj_path] = link

            # Devices are linked, so we can mark services as resolved.
            await self.peer_device.ServicesResolved.set_async(True)
            await self.ServicesResolved.set_async(True)

        if self.connect_check_pairing_required(uuid):
            await self.pair()
        await self.peer_adapter.add_device(self.peer_device)

        try:
            self.connecting_task = asyncio.create_task(task())
            async with asyncio.timeout(self.CONNECTING_TIMEOUT):
                await self.connecting_task
        except asyncio.TimeoutError:
            logging.info(f"Connecting with {self} timed out")

    async def disconnect(self, uuid: Optional[str] = None) -> None:
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

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def Connect(self) -> None:
        await self.connect()

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def Disconnect(self) -> None:
        await self.disconnect()

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def ConnectProfile(self, uuid: str) -> None:
        await self.connect(uuid)

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def DisconnectProfile(self, uuid: str) -> None:
        await self.disconnect(uuid)

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def Pair(self) -> None:
        await self.pair()

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def CancelPairing(self) -> None:
        if not self.pairing_task.done():
            logging.info(f"Canceling pairing with {self}")
        self.pairing_task.cancel()

    @sdbus.dbus_method_async_override()
    @dbus_method_async_except_logging
    async def GetServiceRecords(self) -> list[bytes]:
        return []

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Address(self) -> str:
        return self.address

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def AddressType(self) -> str:
        return "public"

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Name(self) -> str:
        return self.name_

    @Name.setter_private
    def Name_setter(self, value):
        self.name_ = value

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Icon(self) -> str:
        return self.icon

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Alias(self) -> str:
        return self.name

    @Alias.setter
    def Alias_setter(self, value):
        self.name = value

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Class(self) -> int:
        return self.class_

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Appearance(self) -> int:
        return self.appearance

    @Appearance.setter_private
    def Appearance_setter(self, value):
        self.appearance = value

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def UUIDs(self) -> list[str]:
        return self.uuids

    @UUIDs.setter_private
    def UUIDs_setter(self, value):
        self.uuids = value

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Paired(self) -> bool:
        return self.paired

    @Paired.setter_private
    def Paired_setter(self, value):
        self.paired = value

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Bonded(self) -> bool:
        return self.bonded

    @Bonded.setter_private
    def Bonded_setter(self, value):
        self.bond = value

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Trusted(self) -> bool:
        return self.trusted

    @Trusted.setter
    def Trusted_setter(self, value):
        self.trusted = value

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Blocked(self) -> bool:
        return self.blocked

    @Blocked.setter
    def Blocked_setter(self, value):
        self.blocked = value

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def WakeAllowed(self) -> bool:
        return self.wake_allowed

    @WakeAllowed.setter
    def WakeAllowed_setter(self, value):
        self.wake_allowed = value

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Connected(self) -> bool:
        return self.connected

    @Connected.setter_private
    def Connected_setter(self, value):
        self.connected = value

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Adapter(self) -> str:
        return self.adapter.get_object_path()

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def LegacyPairing(self) -> bool:
        return False

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def CablePairing(self) -> bool:
        return False

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def Modalias(self) -> str:
        return "usb:v1D6Bp0246d0537"

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def RSSI(self) -> int:
        return self.rssi

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def TxPower(self) -> int:
        return self.tx_power or 0

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def ManufacturerData(self) -> dict[str, tuple[str, object]]:
        return self.manufacturer_data

    @ManufacturerData.setter_private
    def ManufacturerData_setter(self, value):
        self.manufacturer_data = value

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def ServiceData(self) -> dict[str, tuple[str, Any]]:
        return self.service_data

    @ServiceData.setter_private
    def ServiceData_setter(self, value):
        self.service_data = value

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def ServicesResolved(self) -> bool:
        return self.services_resolved

    @ServicesResolved.setter_private
    def ServicesResolved_setter(self, value):
        self.services_resolved = value

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def AdvertisingFlags(self) -> bytes:
        return self.advertising_flags

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def AdvertisingData(self) -> dict[str, tuple[str, object]]:
        return self.advertising_data

    @sdbus.dbus_property_async_override()
    @dbus_property_async_except_logging
    def PreferredBearer(self) -> str:
        return self.bearer

    @PreferredBearer.setter
    def PreferredBearer_setter(self, value):
        self.bearer = value
