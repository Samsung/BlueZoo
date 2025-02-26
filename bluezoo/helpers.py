# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import asyncio
import re
import weakref
from functools import partial

import sdbus
from sdbus.dbus_proxy_async_property import DbusPropertyAsyncProxyBind
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


class DBusClientMixin:
    """Helper class for D-Bus client objects."""

    def __init__(self, service: str, path: str):
        super().__init__()
        # Connect our client to the D-Bus service.
        self._connect(service, path)

    async def _props_watch(self):
        interfaces = self.__class__.mro()
        async for x in self.properties_changed.catch():
            for k, v in parse_properties_changed(interfaces, x).items():
                getattr(self, k).dbus_property.cached_value = v

    def _props_watch_task_cancel(self):
        self._props_watch_task.cancel()

    async def properties_setup_sync_task(self):
        """Synchronize cached properties with the D-Bus service."""
        for k, v in (await self.properties_get_all_dict()).items():
            getattr(self, k).dbus_property.cached_value = v
        self._props_watch_task = asyncio.create_task(self._props_watch())
        weakref.finalize(self, self._props_watch_task_cancel)

    def get_client(self) -> tuple[str, str]:
        """Return the client destination."""
        return self._dbus.service_name, self._dbus.object_path


def DbusPropertyAsyncProxyBind_get(self, default=None):
    """Return the property value or the default value."""
    return getattr(self.dbus_property, "cached_value", default)
# Bind the property getter to the DbusPropertyAsyncProxyBind class.
DbusPropertyAsyncProxyBind.get = DbusPropertyAsyncProxyBind_get


# Method decorator that sets the Unprivileged flag by default.
dbus_method_async = partial(sdbus.dbus_method_async,
                            flags=sdbus.DbusUnprivilegedFlag)

# Property decorator that sets the EmitsChange flag by default.
dbus_property_async = partial(sdbus.dbus_property_async,
                              flags=sdbus.DbusPropertyEmitsChangeFlag)


def setup_default_bus(address: str):
    """Set the default D-Bus bus based on the given address."""
    if address == "system":
        bus = sdbus.sd_bus_open_system()
    if address == "session":
        bus = sdbus.sd_bus_open_user()
    sdbus.set_default_bus(bus)
    return bus


def validate_bt_address(address: str):
    """Validate the given Bluetooth address."""
    re_bt_address = re.compile(r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
    if re_bt_address.match(address) is None:
        raise ValueError("Invalid Bluetooth address")
    return address


def expand_bt_uuid(uuid: str):
    """Expand the given Bluetooth UUID."""
    re_bt_uuid = re.compile(r"^(0x)?([0-9A-Fa-f]{4})$")
    if match := re_bt_uuid.match(uuid):
        uuid = match.group(2).lower()
        return f"0000{uuid}-0000-1000-8000-00805f9b34fb"
    return uuid
