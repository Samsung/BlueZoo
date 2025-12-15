# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

from ..interfaces.MediaEndpoint import MediaEndpointInterface
from ..utils import DBusClientMixin


class MediaEndpointClient(DBusClientMixin, MediaEndpointInterface):
    """D-Bus client for media endpoint."""

    def __init__(self, service, path, properties, service_lost_callback):
        super().__init__(service, path, service_lost_callback)
        self.properties = properties

    def __str__(self):
        props = self.properties.copy()
        if caps := props.get("Capabilities"):
            props["Capabilities"] = (caps[0], caps[1].hex())
        props = " ".join(f"{k}={v[1]}" for k, v in props.items())
        return f"endpoint[{props}]"
