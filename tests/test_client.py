#!/usr/bin/env -S python3 -X faulthandler
# SPDX-FileCopyrightText: 2025 BlueZoo developers
# SPDX-License-Identifier: GPL-2.0-only

import asyncio
import contextlib
import os
import sys
import unittest

from bluezoo import bluezoo


class AsyncProcessContext:
    """Async context manager for subprocesses."""

    def __init__(self, proc):
        self.proc = proc

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        with contextlib.suppress(ProcessLookupError):
            self.proc.terminate()
        if x := await self.proc.wait():
            msg = f"Process exited with status {x}"
            raise RuntimeError(msg)

    async def __read(self, readline=False):
        if readline:
            return await self.proc.stdout.readline()
        return await self.proc.stdout.read(4096)

    async def expect(self, data: str, timeout=1.0, eol=True) -> str:  # noqa: ASYNC109
        """Read output until expected text is found or timeout occurs."""
        output = b""
        needle = data.encode()
        start = asyncio.get_event_loop().time()
        while True:
            diff = timeout - (asyncio.get_event_loop().time() - start)
            if diff <= 0:
                msg = f"Timeout waiting for '{data}' in output"
                raise TimeoutError(msg)
            try:
                line = await asyncio.wait_for(self.__read(eol), timeout=diff)
                sys.stdout.buffer.write(line)
                sys.stdout.flush()
                if not line:  # EOF
                    break
                output += line
                if needle in output:
                    break
            except TimeoutError:
                continue
        return output.decode(errors="ignore")

    async def write(self, data: str, end="\n"):
        self.proc.stdin.write((data + end).encode())
        await self.proc.stdin.drain()


class ClientContext(AsyncProcessContext):
    """Async context manager for BlueZ client."""

    def __init__(self, *args: str, agent="NoInputNoOutput"):
        self.agent = agent
        self.args = args

    async def __aenter__(self):
        self.proc = await asyncio.create_subprocess_exec(
            "bluetoothctl", f"--agent={self.agent}", *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE)
        return self

    async def get_version(self) -> float:
        """Get client version."""
        await self.write("version")
        return float((await self.expect("Version")).splitlines()[-1].split()[1])


class BluetoothMockTestCase(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):

        # Start a private D-Bus session and get the address.
        self._bus = await asyncio.create_subprocess_exec(
            "dbus-daemon", "--session", "--print-address",
            stdout=asyncio.subprocess.PIPE)
        assert self._bus.stdout is not None, "D-Bus daemon process's stdout is None"
        address = await self._bus.stdout.readline()

        # Force unbuffered output in all Python processes.
        os.environ["PYTHONUNBUFFERED"] = "1"
        # Update environment with D-Bus address.
        os.environ["DBUS_SYSTEM_BUS_ADDRESS"] = address.strip().decode("utf-8")

        # Start mock with two adapters.
        await bluezoo.startup(
            adapters=["00:00:00:11:11:11", "00:00:00:22:22:22"],
            auto_enable=True,
            scan_interval=1)

    async def asyncTearDown(self):
        await bluezoo.shutdown()
        self._bus.terminate()
        await self._bus.wait()
        # Make sure that all tasks were properly handled. The list shall
        # contain the asyncTearDown() task only - we are in it right now.
        self.assertEqual(len(asyncio.all_tasks()), 1)

    async def test_alias(self):
        async with ClientContext() as ctl:
            await ctl.write("select 00:00:00:11:11:11")

            await ctl.write("system-alias WaterDeer")
            await ctl.expect("Changing WaterDeer succeeded")

            await ctl.write("show")
            await ctl.expect("Name: Alligator's Android")
            await ctl.expect("Alias: WaterDeer")

    async def test_agent(self):
        async with ClientContext() as ctl:
            # Wait for the default agent to be registered.
            await ctl.expect("Agent registered")

            await ctl.write("agent off")
            await ctl.expect("Agent unregistered")
            # Without an agent, pairing is not possible.
            await ctl.expect("Controller 00:00:00:11:11:11 Pairable: no")
            await ctl.expect("Controller 00:00:00:22:22:22 Pairable: no")

            await ctl.write("agent NoInputNoOutput")
            await ctl.expect("Agent registered")
            await ctl.expect("Controller 00:00:00:11:11:11 Pairable: yes")
            await ctl.expect("Controller 00:00:00:22:22:22 Pairable: yes")

            await ctl.write("default-agent")
            await ctl.expect("Default agent request successful")

    async def test_discoverable(self):
        async with ClientContext() as ctl:

            await ctl.write("discoverable on")
            await ctl.expect("Changing discoverable on succeeded")

            await ctl.write("discoverable off")
            await ctl.expect("Changing discoverable off succeeded")

    async def test_discoverable_timeout(self):
        async with ClientContext() as ctl:

            await ctl.write("discoverable on")
            # Verify that the timeout works as expected.
            await ctl.write("discoverable-timeout 1")
            await ctl.expect("Discoverable: no", timeout=1.5)

    async def test_scan(self):
        async with ClientContext() as ctl:

            await ctl.write("select 00:00:00:11:11:11")
            await ctl.write("discoverable on")
            await ctl.expect("Changing discoverable on succeeded")

            await ctl.write("select 00:00:00:22:22:22")
            await ctl.write("scan on")
            await ctl.expect("Discovery started")
            await ctl.expect("Device 00:00:00:11:11:11")

            await ctl.write("scan off")
            await ctl.expect("Discovery stopped")

    async def test_scan_le(self):
        async with ClientContext() as ctl:

            await ctl.write("select 00:00:00:11:11:11")
            await ctl.write("advertise on")
            await ctl.expect("Advertising object registered")

            await ctl.write("select 00:00:00:22:22:22")
            await ctl.write("scan le")
            await ctl.expect("Discovery started")
            await ctl.expect("Device 00:00:00:11:11:11")

    async def test_advertise_le(self):
        async with ClientContext() as ctl:

            await ctl.write("select 00:00:00:11:11:11")
            await ctl.write("advertise.name BLE-Device")
            await ctl.write("advertise.appearance 0x00a0")
            await ctl.write("advertise.uuids 0xFFF1")
            await ctl.write("advertise.service 0xFFF1 0xDE 0xAD 0xBE 0xEF")
            await ctl.write("advertise.discoverable on")
            await ctl.write("advertise peripheral")
            await ctl.expect("Advertising object registered")

            await ctl.write("select 00:00:00:22:22:22")
            await ctl.write("scan le")
            await ctl.expect("Discovery started")
            await ctl.expect("Device 00:00:00:11:11:11")

            await ctl.write("info 00:00:00:11:11:11")
            await ctl.expect("Name: BLE-Device")
            await ctl.expect("Appearance: 0x00a0")
            await ctl.expect("ServiceData.0000fff1-0000-1000-8000-00805f9b34fb:")

            # Update the advertisement data and verify that the changes
            # are visible to the scanner.
            await ctl.write("select 00:00:00:11:11:11")
            await ctl.write("advertise.name BLE-Device-42")

            await ctl.write("select 00:00:00:22:22:22")
            # The scan interval is 1 second, so we need to wait for the
            # scanner to pick up the new advertisement data.
            await ctl.expect("Name: BLE-Device-42", timeout=1.5)

            await ctl.write("select 00:00:00:11:11:11")
            await ctl.write("advertise off")
            await ctl.expect("Advertising object unregistered")

    async def test_gatt_application(self):
        async with ClientContext() as ctl:

            await ctl.write("gatt.register-service 0xF100")
            await ctl.expect("Primary (yes/no):", eol=False)
            await ctl.write("yes")

            await ctl.write("gatt.register-characteristic 0xF110 read,write")
            await ctl.expect("Enter value:", eol=False)
            await ctl.write("0x43 0x48 0x41 0x52 0x41 0x43 0x54 0x45 0x52")

            await ctl.write("gatt.register-characteristic 0xF120 read,notify")
            await ctl.expect("Enter value:", eol=False)
            await ctl.write("0x05 0x06 0x07 0x08")

            await ctl.write("gatt.register-descriptor 0xF121 read")
            await ctl.expect("Enter value:", eol=False)
            await ctl.write("0x44 0x45 0x53 0x43 0x52 0x49 0x50 0x54 0x4F 0x52")

            await ctl.write("gatt.register-application")
            # Verify that the service handle was assigned.
            await ctl.expect("/org/bluez/app/service0")
            # Verify that new service was added to the adapter.
            await ctl.expect("UUIDs: 0000f100-0000-1000-8000-00805f9b34fb")

            await ctl.write("gatt.unregister-application")
            await ctl.expect("Application unregistered")

    async def test_pair(self):
        async with ClientContext() as ctl:

            await ctl.write("select 00:00:00:11:11:11")
            await ctl.write("discoverable on")
            await ctl.expect("Changing discoverable on succeeded")

            await ctl.write("select 00:00:00:22:22:22")
            await ctl.write("scan on")
            await ctl.expect("Discovery started")
            await ctl.expect("Device 00:00:00:11:11:11")

            await ctl.write("trust 00:00:00:11:11:11")
            await ctl.write("pair 00:00:00:11:11:11")
            await ctl.expect("Pairing successful")

            # Verify that the device is paired.
            await ctl.write("info 00:00:00:11:11:11")
            await ctl.expect("Device 00:00:00:11:11:11 (public)")
            await ctl.expect("Paired: yes")
            await ctl.expect("Trusted: yes")

            await ctl.write("select 00:00:00:11:11:11")
            # Verify that the device is paired.
            await ctl.write("info 00:00:00:22:22:22")
            await ctl.expect("Device 00:00:00:22:22:22 (public)")
            await ctl.expect("Paired: yes")

    async def test_connect(self):
        async with ClientContext() as ctl:

            await ctl.write("select 00:00:00:11:11:11")
            await ctl.write("discoverable on")
            await ctl.expect("Changing discoverable on succeeded")

            await ctl.write("select 00:00:00:22:22:22")
            await ctl.write("scan on")
            await ctl.expect("Discovery started")
            await ctl.expect("Device 00:00:00:11:11:11")

            await ctl.write("connect 00:00:00:11:11:11")
            # The device is not trusted, so we need to accept the pairing.
            await ctl.expect("[agent] Accept pairing (yes/no):", eol=False)
            await ctl.write("yes")

            await ctl.expect("Connection successful")

            # Verify that the device is connected.
            await ctl.write("info 00:00:00:11:11:11")
            await ctl.expect("Device 00:00:00:11:11:11 (public)")
            await ctl.expect("Connected: yes")

            await ctl.write("select 00:00:00:11:11:11")
            # Verify that the device is connected.
            await ctl.write("info 00:00:00:22:22:22")
            await ctl.expect("Device 00:00:00:22:22:22 (public)")
            await ctl.expect("Connected: yes")

    async def test_disconnect(self):
        async with ClientContext() as ctl:

            await ctl.write("select 00:00:00:11:11:11")
            await ctl.write("discoverable on")

            await ctl.write("select 00:00:00:22:22:22")
            await ctl.write("scan on")
            await ctl.expect("Device 00:00:00:11:11:11")

            await ctl.write("connect 00:00:00:11:11:11")
            # The device is not trusted, so we need to accept the pairing.
            await ctl.expect("[agent] Accept pairing (yes/no):", eol=False)
            await ctl.write("yes")

            await ctl.expect("Connection successful")

            # Remove the device - this should trigger disconnection.
            await ctl.write("remove 00:00:00:11:11:11")
            await ctl.expect("Device has been removed")

            # The device is not longer available on our side, but verify that
            # on the other side (the other adapter) our device is disconnected.
            await ctl.write("select 00:00:00:11:11:11")
            await ctl.write("info 00:00:00:22:22:22")
            await ctl.expect("Connected: no")

    async def test_connect_gatt(self):
        async with ClientContext() as ctl:

            await ctl.write("select 00:00:00:11:11:11")
            # Setup GATT primary service.
            await ctl.write("gatt.register-service 0xF100")
            await ctl.expect("Primary (yes/no):", eol=False)
            await ctl.write("yes")
            # Setup GATT characteristic with read/write permissions.
            await ctl.write("gatt.register-characteristic 0xF110 read,write")
            await ctl.expect("Enter value:", eol=False)
            await ctl.write("0x43 0x48 0x41 0x52 0x41 0x43 0x54 0x45 0x52")
            # Setup GATT characteristic with read/notify permissions.
            await ctl.write("gatt.register-characteristic 0xF120 read,notify")
            await ctl.expect("Enter value:", eol=False)
            await ctl.write("0x52 0x45 0x41 0x44")
            # Setup GATT descriptor with read/write permissions.
            await ctl.write("gatt.register-descriptor 0xF121 read")
            await ctl.expect("Enter value:", eol=False)
            await ctl.write("0x44 0x45 0x53 0x43")
            # Register GATT application.
            await ctl.write("gatt.register-application")
            # Verify that new service was added to the adapter.
            await ctl.expect("UUIDs: 0000f100-0000-1000-8000-00805f9b34fb")
            # Advertising GATT service on first adapter.
            await ctl.write("advertise.uuids 0xF100")
            await ctl.write("advertise.discoverable on")
            await ctl.write("advertise peripheral")
            await ctl.expect("Advertising object registered")

            # Scan for the GATT service on second adapter.
            await ctl.write("select 00:00:00:22:22:22")
            await ctl.write("scan le")
            await ctl.expect("Discovery started")
            await ctl.expect("Device 00:00:00:11:11:11")

            # Connect to the GATT service.
            await ctl.write("connect 00:00:00:11:11:11")
            await ctl.expect("Connection successful")

            # Verify that we can read 0xF110 characteristic.
            await ctl.write("gatt.select-attribute 0000f110-0000-1000-8000-00805f9b34fb")
            await ctl.write("gatt.read")
            await ctl.expect("CHARACTER")
            # Verify error when reading at invalid offset.
            await ctl.write("gatt.read 32")
            await ctl.expect("Failed to read: org.bluez.Error.InvalidOffset")
            # Verify that we can write at specified offset.
            await ctl.write("gatt.write '0x61 0x63 0x74' 4")
            await ctl.expect("act")
            # Verify that the value was correctly written.
            await ctl.write("gatt.read")
            await ctl.expect("CHARact")

            # Verify notifications from 0xF120 characteristic.
            await ctl.write("gatt.select-attribute 0000f120-0000-1000-8000-00805f9b34fb")
            await ctl.write("gatt.notify on")
            await ctl.expect("Notify started")

            # Verify that we can read 0xF121 descriptor.
            await ctl.write("gatt.select-attribute 0000f121-0000-1000-8000-00805f9b34fb")
            await ctl.write("gatt.read")
            await ctl.expect("DESC")
            # Verify that we can write at specified offset.
            await ctl.write("gatt.write '0x4f 0x4e 0x45' 1")
            # Verify that the value was correctly written.
            await ctl.write("gatt.read")
            await ctl.expect("DONE")

    async def test_connect_gatt_indicate_call(self):

        srv = AsyncProcessContext(await asyncio.create_subprocess_exec(
            "tests/gatt/server.py", "--adapter=hci1", "--service=0xF100", "--char=0xF110",
            "--primary", "--flag=read", "--flag=indicate", "--mutate=0.1",
            stdout=asyncio.subprocess.PIPE))
        await srv.expect("Registered 0xF100 on hci1")

        adv = AsyncProcessContext(await asyncio.create_subprocess_exec(
            "tests/gatt/advertise.py", "--adapter=hci1", "--service=0xF100",
            "--discoverable",
            stdout=asyncio.subprocess.PIPE))
        await adv.expect("Advertising 0xF100 on hci1")

        async with srv, adv, ClientContext() as ctl:

            # Scan for the GATT service on first adapter.
            await ctl.write("select 00:00:00:11:11:11")
            await ctl.write("scan le")
            await ctl.expect("Discovery started")
            await ctl.expect("Device 00:00:00:22:22:22")

            # Connect to the GATT service.
            await ctl.write("connect 00:00:00:22:22:22")
            await ctl.expect("Connection successful")

            # Verify notifications from 0xF001 characteristic.
            await ctl.write("gatt.select-attribute 0000f110-0000-1000-8000-00805f9b34fb")
            await ctl.write("gatt.notify on")
            await ctl.expect("Notify started")

            # Verify that the indication was confirmed via D-Bus call.
            await srv.expect("Indication confirmed via D-Bus call")

            await ctl.write("gatt.notify off")
            await ctl.expect("Notify stopped")

    async def test_connect_gatt_indicate_socket(self):

        srv = AsyncProcessContext(await asyncio.create_subprocess_exec(
            "tests/gatt/server.py", "--adapter=hci1", "--service=0xF100", "--char=0xF110",
            "--primary", "--flag=read", "--flag=indicate", "--mutate=0.1", "--with-sockets",
            stdout=asyncio.subprocess.PIPE))
        await srv.expect("Registered 0xF100 on hci1")

        adv = AsyncProcessContext(await asyncio.create_subprocess_exec(
            "tests/gatt/advertise.py", "--adapter=hci1", "--service=0xF100",
            "--discoverable",
            stdout=asyncio.subprocess.PIPE))
        await adv.expect("Advertising 0xF100 on hci1")

        async with srv, adv, ClientContext() as ctl:

            # Scan for the GATT service on first adapter.
            await ctl.write("select 00:00:00:11:11:11")
            await ctl.write("scan le")
            await ctl.expect("Discovery started")
            await ctl.expect("Device 00:00:00:22:22:22")

            # Connect to the GATT service.
            await ctl.write("connect 00:00:00:22:22:22")
            await ctl.expect("Connection successful")

            # Verify notifications from 0xF001 characteristic.
            await ctl.write("gatt.select-attribute 0000f110-0000-1000-8000-00805f9b34fb")
            await ctl.write("gatt.notify on")
            await ctl.expect("Notify started")

            # Verify that the indication was confirmed via socket.
            await srv.expect("Indication confirmation via socket: 01")

            await ctl.write("gatt.notify off")
            await ctl.expect("Notify stopped")

    async def test_media_endpoint(self):
        async with ClientContext() as ctl:

            # This check requires BlueZ >= 5.86 due to a bug in the player subsystem
            # of the client code - it does not support multiple adapters.
            if await ctl.get_version() < 5.86:
                self.skipTest("Test case requires BlueZ >= 5.86")

            uuid = "0000110a-0000-1000-8000-00805f9b34fb"  # Audio Sink
            await ctl.write(f"endpoint.register {uuid} 0x00 '0xFF 0xFF 0x02 0x40'")
            await ctl.expect("Enter Metadata", eol=False)
            await ctl.write("no")
            await ctl.expect("Auto Accept", eol=False)
            await ctl.write("no")
            await ctl.expect("Max Transports", eol=False)
            await ctl.write("auto")
            await ctl.expect("Locations", eol=False)
            await ctl.write("0")
            await ctl.expect("Supported Context", eol=False)
            await ctl.write("0")
            await ctl.expect("Context", eol=False)
            await ctl.write("0")
            await ctl.expect("CIG", eol=False)
            await ctl.write("auto")
            await ctl.expect("CIS", eol=False)
            await ctl.write("auto")
            # Verify that the endpoint was registered on both adapters.
            await ctl.expect("Endpoint /local/endpoint/ep0 registered")
            await ctl.expect("Endpoint /local/endpoint/ep0 registered")

            await ctl.write("endpoint.unregister /local/endpoint/ep0")
            # Verify that endpoint was deregistered on both adapters.
            await ctl.expect("Endpoint /local/endpoint/ep0 unregistered")
            await ctl.expect("Endpoint /local/endpoint/ep0 unregistered")


if __name__ == "__main__":
    unittest.main()
