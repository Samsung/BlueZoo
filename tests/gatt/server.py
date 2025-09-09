#!/usr/bin/env python3

import asyncio
import os
import signal
import socket
from argparse import ArgumentParser

import sdbus

from bluezoo.interfaces.GattManager import GattManagerInterface
from bluezoo.utils import setup_default_bus

parser = ArgumentParser()
parser.add_argument('--adapter', metavar='ADAPTER', default='hci0',
                    help="Bluetooth adapter to use; default: %(default)s")
parser.add_argument('--timeout', metavar='SECONDS', type=int, default=60,
                    help="GATT service availability timeout; default: %(default)s")
parser.add_argument('--service', metavar='UUID', default='0xF000',
                    help="GATT service UUID; default: %(default)s")
parser.add_argument('--char', metavar='UUID', default='0xF001',
                    help="GATT characteristic UUID; default: %(default)s")
parser.add_argument('--primary', action='store_true',
                    help="export service as primary")
parser.add_argument('--flag', action='append', required=True, choices=[
    "broadcast", "read", "write-without-response", "write", "notify", "indicate",
    "authenticated-signed-writes", "extended-properties", "reliable-write",
    "writable-auxiliaries", "encrypt-read", "encrypt-write", "encrypt-notify",
    "encrypt-indicate", "encrypt-authenticated-read", "encrypt-authenticated-write",
    "encrypt-authenticated-notify", "encrypt-authenticated-indicate", "secure-read",
    "secure-write", "secure-notify", "secure-indicate", "authorize"],
    help="export characteristic with specific flags")
parser.add_argument('--value', metavar='HEX', type=bytearray.fromhex, default=bytearray(),
                    help="initial GATT characteristic value")
parser.add_argument('--mutate', metavar='SECONDS', type=float,
                    help="mutate the GATT characteristic value repeatedly")
parser.add_argument('--with-sockets', action='store_true',
                    help="use sockets for communication")

args = parser.parse_args()
loop = asyncio.new_event_loop()
setup_default_bus("system")


class ServiceInterface(
        sdbus.DbusInterfaceCommonAsync,
        interface_name='org.bluez.GattService1'):

    @sdbus.dbus_property_async(
        property_signature='s',
        flags=sdbus.DbusPropertyEmitsChangeFlag)
    def UUID(self) -> str:
        return args.service

    @sdbus.dbus_property_async(
        property_signature='b',
        flags=sdbus.DbusPropertyEmitsChangeFlag)
    def Primary(self) -> bool:
        return args.primary


class CharacteristicInterface(
        sdbus.DbusInterfaceCommonAsync,
        interface_name='org.bluez.GattCharacteristic1'):

    notifying = False
    value = args.value

    f_write = None
    f_notify = None

    @sdbus.dbus_method_async(
        input_signature='a{sv}',
        input_args_names=['options'],
        result_signature='ay',
        result_args_names=['r0'],
        flags=sdbus.DbusUnprivilegedFlag)
    async def ReadValue(self, options: dict[str, tuple[str, object]]) -> bytes:
        print("Read characteristic with options:", options)
        return self.value

    @sdbus.dbus_method_async(
        input_signature='aya{sv}',
        input_args_names=['value', 'options'],
        flags=sdbus.DbusUnprivilegedFlag)
    async def WriteValue(self, value: bytes, options: dict[str, tuple[str, object]]):
        print("Write characteristic with options:", options)
        self.value = bytearray(value)

    @sdbus.dbus_method_async(
        input_signature='a{sv}',
        input_args_names=['options'],
        result_signature='hq',
        result_args_names=['r0', 'r1'],
        flags=sdbus.DbusUnprivilegedFlag)
    async def AcquireWrite(self, options: dict[str, tuple[str, object]]) -> tuple[int, int]:
        print("Acquire write with options:", options)
        f1, f2 = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.f_write = f1
        mtu = 23

        def reader():
            if data := f1.recv(mtu):
                print("Received write data:", data.hex())
                self.value = bytearray(data)
            else:
                self.f_write = None
                f1.close()

        loop.add_reader(f1.fileno(), reader)
        return os.dup(f2.fileno()), mtu

    @sdbus.dbus_method_async(
        input_signature='a{sv}',
        input_args_names=['options'],
        result_signature='hq',
        result_args_names=['r0', 'r1'],
        flags=sdbus.DbusUnprivilegedFlag)
    async def AcquireNotify(self, options: dict[str, tuple[str, object]]) -> tuple[int, int]:
        print("Acquire notify with options:", options)
        f1, f2 = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.f_notify = f1
        mtu = 23

        def reader():
            if data := f1.recv(mtu):
                print("Indication confirmation via socket:", data.hex())
            else:
                self.f_notify = None
                f1.close()

        loop.add_reader(f1.fileno(), reader)
        return os.dup(f2.fileno()), mtu

    @sdbus.dbus_method_async(
        flags=sdbus.DbusUnprivilegedFlag)
    async def StartNotify(self):
        print("Start characteristic notification")
        await self.Notifying.set_async(True)

    @sdbus.dbus_method_async(
        flags=sdbus.DbusUnprivilegedFlag)
    async def StopNotify(self):
        print("Stop characteristic notification")
        await self.Notifying.set_async(False)

    @sdbus.dbus_method_async(
        flags=sdbus.DbusUnprivilegedFlag)
    async def Confirm(self):
        print("Indication confirmed via D-Bus call")

    @sdbus.dbus_property_async(
        property_signature='s',
        flags=sdbus.DbusPropertyEmitsChangeFlag)
    def UUID(self) -> str:
        return args.char

    @sdbus.dbus_property_async(
        property_signature='o',
        flags=sdbus.DbusPropertyEmitsChangeFlag)
    def Service(self) -> str:
        return "/srv"

    @sdbus.dbus_property_async(
        property_signature='ay',
        flags=sdbus.DbusPropertyEmitsChangeFlag)
    def Value(self) -> bytes:
        return self.value

    @Value.setter_private
    def Value_setter(self, value: bytes):
        self.value = bytearray(value)

    if args.with_sockets and set(args.flag).intersection({'write-without-response'}):
        @sdbus.dbus_property_async(
            property_signature='b',
            flags=sdbus.DbusPropertyEmitsChangeFlag)
        def WriteAcquired(self) -> bool:
            return self.f_write is not None

    if args.with_sockets and set(args.flag).intersection({'notify', 'indicate'}):
        @sdbus.dbus_property_async(
            property_signature='b',
            flags=sdbus.DbusPropertyEmitsChangeFlag)
        def NotifyAcquired(self) -> bool:
            return self.f_notify is not None

    @sdbus.dbus_property_async(
        property_signature='b',
        flags=sdbus.DbusPropertyEmitsChangeFlag)
    def Notifying(self) -> bool:
        return self.notifying

    @Notifying.setter_private
    def Notifying_setter(self, value: bool):
        self.notifying = value

    @sdbus.dbus_property_async(
        property_signature='as',
        flags=sdbus.DbusPropertyEmitsChangeFlag)
    def Flags(self) -> list[str]:
        return args.flag


manager = sdbus.DbusObjectManagerInterfaceAsync()
manager.export_to_dbus("/")

service = ServiceInterface()
manager.export_with_manager("/srv", service)

char = CharacteristicInterface()
manager.export_with_manager("/srv/char", char)

adapter = f"/org/bluez/{args.adapter}"
gatt_manager = GattManagerInterface.new_proxy("org.bluez", adapter)


async def startup():
    await gatt_manager.RegisterApplication("/", {})
    print(f"Registered {args.service} on {args.adapter}")


async def mutate():
    while args.mutate:
        try:
            await asyncio.sleep(args.mutate)
            char.value[-1] = (char.value[-1] + 1) % 256
        except IndexError:
            char.value = bytearray([0])
        if char.f_notify is not None:
            char.f_notify.send(char.value)
            continue
        await char.Value.set_async(char.value)


async def timeout():
    await asyncio.sleep(args.timeout)
    loop.stop()


loop.run_until_complete(startup())
t1 = loop.create_task(timeout())
t2 = loop.create_task(mutate())

loop.add_signal_handler(signal.SIGINT, lambda: loop.stop())
loop.add_signal_handler(signal.SIGTERM, lambda: loop.stop())
loop.run_forever()
