# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import sdbus

from .utils import dbus_method_async_except_logging


class BlueZooAlreadyExistsError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluezoo.Error.AlreadyExists"


class BlueZooDoesNotExistError(sdbus.DbusFailedError):
    dbus_error_name = "org.bluezoo.Error.DoesNotExist"


class BlueZooController(
        sdbus.DbusInterfaceCommonAsync,
        interface_name="org.bluezoo.Manager1"):

    def __init__(self, mock):
        super().__init__()
        self.mock = mock

    @sdbus.dbus_method_async(
        input_signature="ys",
        input_args_names=["id", "address"],
        result_signature="o",
        result_args_names=["adapter"],
        flags=sdbus.DbusUnprivilegedFlag)
    @dbus_method_async_except_logging
    async def AddAdapter(self, id: int, address: str) -> str:
        if id in self.mock.adapters:
            raise BlueZooAlreadyExistsError("Already Exists")
        adapter = await self.mock.add_adapter(id, address)
        return adapter.get_object_path()

    @sdbus.dbus_method_async(
        input_signature="y",
        input_args_names=["id"],
        flags=sdbus.DbusUnprivilegedFlag)
    @dbus_method_async_except_logging
    async def RemoveAdapter(self, id: int):
        if id not in self.mock.adapters:
            raise BlueZooDoesNotExistError("Does Not Exist")
        await self.mock.del_adapter(id)
