# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: MIT

import sdbus

from ..utils import dbus_method_async


class AgentInterface(sdbus.DbusInterfaceCommonAsync,
                     interface_name="org.bluez.Agent1"):

    @dbus_method_async()
    async def Release(self) -> None:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="o",
        input_args_names=("device",),
        result_signature="s",
        result_args_names=('pincode',))
    async def RequestPinCode(self, device: str) -> str:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="os",
        input_args_names=("device", "pincode"))
    async def DisplayPinCode(self, device: str, pincode: str) -> None:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="o",
        input_args_names=("device",),
        result_signature="u",
        result_args_names=('passkey',))
    async def RequestPasskey(self, device: str) -> int:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="ouq",
        input_args_names=("device", "passkey", "entered"))
    async def DisplayPasskey(self, device: str, passkey: int, entered: int) -> None:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="ou",
        input_args_names=("device", "passkey"))
    async def RequestConfirmation(self, device: str, passkey: int) -> None:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="o",
        input_args_names=("device",))
    async def RequestAuthorization(self, device: str) -> None:
        raise NotImplementedError

    @dbus_method_async(
        input_signature="os",
        input_args_names=("device", "uuid"))
    async def AuthorizeService(self, device: str, uuid: str) -> None:
        raise NotImplementedError

    @dbus_method_async()
    async def Cancel(self) -> None:
        raise NotImplementedError
