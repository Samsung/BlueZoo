# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

from .interfaces import DeviceInterface


class Device:

    def __init__(self, adapter):

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
        self.bonded = False
        self.trusted = False
        self.blocked = False
        self.connected = False
        self.services_resolved = False
        self.service_data = {}
        self.uuids = []

        self.iface = DeviceInterface(self)

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
