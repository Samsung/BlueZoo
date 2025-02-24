# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import re
from functools import partial

import sdbus


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
