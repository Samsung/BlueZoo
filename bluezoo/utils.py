# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import asyncio
import logging
import re
import weakref
from enum import IntFlag
from functools import wraps

import sdbus
from sdbus.dbus_proxy_async_interfaces import DbusInterfaceBaseAsync
from sdbus.dbus_proxy_async_property import (DbusLocalPropertyAsync, DbusPropertyAsync,
                                             DbusProxyPropertyAsync, DbusRemoteObjectMeta)
from sdbus.utils import parse_properties_changed


class NoneTask:
    """A class which imitates a task that is done."""

    def __init__(self):
        self._cancelled = False

    def done(self):
        return True

    def cancel(self, msg=None):
        self._cancelled = True

    def cancelled(self):
        return self._cancelled


class DBusPropertyAsyncProxyBindWithCache(DbusProxyPropertyAsync):

    def __init__(self, dbus_property, local_object, proxy_meta):
        super().__init__(dbus_property, proxy_meta)
        self.local_object_ref = weakref.ref(local_object)
        if not hasattr(local_object, "_cache"):
            local_object._cache = {}

    def cache(self, value):
        """Cache the property value."""
        local_object = self.local_object_ref()
        property_name = self.dbus_property.property_name
        local_object._cache[property_name] = value

    def get(self, default=None):
        """Return the property value or the default value."""
        local_object = self.local_object_ref()
        property_name = self.dbus_property.property_name
        return local_object._cache.get(property_name, default)

    async def set_async(self, value):
        await super().set_async(value)
        self.cache(value)


def DbusPropertyAsync__get__(self, obj, obj_class):
    if obj is None:
        return self
    dbus_meta = obj._dbus
    if isinstance(dbus_meta, DbusRemoteObjectMeta):
        return DBusPropertyAsyncProxyBindWithCache(self, obj, dbus_meta)
    else:
        return DbusLocalPropertyAsync(self, obj)


# Monkey-patch the library to support property caching.
DbusPropertyAsync.__get__ = DbusPropertyAsync__get__


class DBusClientMixin(DbusInterfaceBaseAsync):
    """Helper class for D-Bus client objects."""

    def __init__(self, service: str, path: str):
        super().__init__()
        # Connect our client to the D-Bus service.
        self._connect(service, path)

    async def _props_watch(self):
        interfaces = self.__class__.mro()
        async for x in self.properties_changed.catch():
            for k, v in parse_properties_changed(interfaces, x).items():
                getattr(self, k).cache(v)

    def _props_watch_task_cancel(self):
        self._props_watch_task.cancel()

    async def properties_setup_sync_task(self):
        """Synchronize cached properties with the D-Bus service."""
        properties = await self.properties_get_all_dict()
        for k, v in properties.items():
            getattr(self, k).cache(v)
        self._props_watch_task = asyncio.create_task(self._props_watch())
        weakref.finalize(self, self._props_watch_task_cancel)

    def get_client(self) -> str:
        return self._dbus.service_name

    def get_object_path(self) -> str:
        return self._dbus.object_path


def dbus_method_async_except_logging(func):
    """Decorator that logs exceptions from D-Bus methods."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except sdbus.SdBusBaseError:
            raise  # Propagate D-Bus errors.
        except Exception:
            logging.exception(f"Error in D-Bus method {func.__name__}")
    return wrapper


def dbus_property_async_except_logging(func):
    """Decorator that logs exceptions from D-Bus properties."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except sdbus.SdBusBaseError:
            raise  # Propagate D-Bus errors.
        except Exception:
            logging.exception(f"Error in D-Bus property {func.__name__}")
    return wrapper


def setup_default_bus(address: str):
    """Set the default D-Bus bus based on the given address."""
    if address == "system":
        bus = sdbus.sd_bus_open_system()
    if address == "session":
        bus = sdbus.sd_bus_open_user()
    sdbus.set_default_bus(bus)
    return bus


class BluetoothAddress(str):
    """Validate the given Bluetooth address."""

    re_address = re.compile(r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")

    def __new__(cls, address: str):
        if cls.re_address.match(address) is None:
            raise ValueError("Invalid Bluetooth address")
        return super().__new__(cls, address)


class BluetoothClass(int):
    """Bluetooth Class of Device."""

    class Major(IntFlag):
        Miscellaneous = 0x00
        Computer = 0x01
        Phone = 0x02
        NetworkAccessPoint = 0x03
        AudioVideo = 0x04
        Peripheral = 0x05
        Imaging = 0x06
        Wearable = 0x07
        Toy = 0x08
        Health = 0x09
        Uncategorized = 0x1F

    class Service(IntFlag):
        LimitedDiscoverableMode = 1 << 0
        LEAudio = 1 << 1
        ReservedForFutureUse = 1 << 2
        Positioning = 1 << 3     # Location identification
        Networking = 1 << 4      # LAN, Ad hoc, etc.
        Rendering = 1 << 5       # Printing, Speakers, etc.
        Capturing = 1 << 6       # Scanner, Microphone, etc.
        ObjectTransfer = 1 << 7  # v-Inbox, v-Folder, etc.
        Audio = 1 << 8           # Speaker, Microphone, Headset, etc.
        Telephony = 1 << 9       # Cordless telephony, Modem, etc.
        Information = 1 << 10    # WEB server, WAP server, etc.

    def __new__(cls, major: int = 0, minor: int = 0, services: int = 0):
        return super().__new__(cls, (((services & 0x7FF) << 13) |
                                     ((major & 0x1F) << 8) |
                                     ((minor & 0x3F) << 2)))

    def __add__(self, other):
        if not isinstance(other, BluetoothClass.Service):
            raise TypeError("Can only add BluetoothClass.Service")
        return BluetoothClass(self.major, self.minor, self.services | other)

    def __sub__(self, other):
        if not isinstance(other, BluetoothClass.Service):
            raise TypeError("Can only subtract BluetoothClass.Service")
        return BluetoothClass(self.major, self.minor, self.services & ~other)

    @property
    def icon(self):
        """Icon name for the Bluetooth Class."""
        if self.major == BluetoothClass.Major.Computer:
            return "computer"
        if self.major == BluetoothClass.Major.Phone:
            return "phone"
        if self.major == BluetoothClass.Major.NetworkAccessPoint:
            return "network-wireless"
        if self.major == BluetoothClass.Major.AudioVideo:
            return "audio-card"
        if self.major == BluetoothClass.Major.Peripheral:
            return "input-keyboard"
        if self.major == BluetoothClass.Major.Imaging:
            return "camera-photo"
        return "bluetooth"

    @property
    def major(self):
        return BluetoothClass.Major((self >> 8) & 0x1F)

    @property
    def minor(self):
        return (self >> 2) & 0x3F

    @property
    def services(self):
        return (self >> 13) & 0x7FF


class BluetoothUUID(str):
    """Expand the given Bluetooth UUID to the full 128-bit form."""

    re_uuid_full = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    re_uuid_hex = re.compile(r"^(0x)?([0-9a-f]{1,8})$")

    def __new__(cls, uuid: str):
        uuid = uuid.lower()  # Normalize the UUID to lowercase.
        if match := cls.re_uuid_hex.match(uuid):
            v = hex(int(match.group(2), 16))[2:].zfill(8)
            uuid = v + "-0000-1000-8000-00805f9b34fb"
        elif not cls.re_uuid_full.match(uuid):
            raise ValueError("Invalid Bluetooth UUID")
        return super().__new__(cls, uuid)
