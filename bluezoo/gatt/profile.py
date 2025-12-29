# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

from ..interfaces.GattProfile import GattProfileInterface
from ..utils import DBusClientMixin


class GattProfileClient(DBusClientMixin, GattProfileInterface):
    """D-Bus client for GATT profile."""

    def __init__(self, service, path):
        super().__init__(service, path)
